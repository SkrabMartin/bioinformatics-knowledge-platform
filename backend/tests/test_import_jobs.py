from datetime import UTC, datetime, timedelta

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.services import GeneIngestionService
from app.ingestion.worker import ImportWorker
from app.integrations.errors import UpstreamNotFoundError, UpstreamUnavailableError
from app.integrations.http import RetryingJsonClient
from app.models import Gene
from app.models.import_job import ImportJobItem
from app.schemas.import_job import ImportJobCreate
from app.services.errors import ConflictError
from app.services.import_jobs import ImportJobService
from tests.test_ingestion import FakeGeneProvider


def batch(**overrides: object) -> ImportJobCreate:
    return ImportJobCreate.model_validate(
        {
            "entity_type": "gene",
            "identifiers": ["TP53", "BRCA1"],
            "taxonomy_id": "9606",
            **overrides,
        }
    )


def test_batch_identity_validation_and_atomic_idempotency(session: Session) -> None:
    service = ImportJobService(session)
    payload = batch(identifiers=[" TP53 ", "TP53"], idempotency_key="test-batch")
    job = service.create(payload)
    assert job.counts == {"pending": 1, "total": 1}
    assert service.create(payload).id == job.id
    with pytest.raises(ConflictError):
        service.create(batch(idempotency_key="test-batch"))
    assert service.browse(1, 1).total == 1
    assert service.items(job.id, 1, 1).items[0].identifier == "TP53"


@pytest.mark.parametrize(
    "overrides",
    [
        {"identifiers": []},
        {"identifiers": ["TP53"] * 101},
        {"identifiers": ["TP53[sym] OR *"]},
        {"taxonomy_id": None},
        {"entity_type": "protein", "identifiers": ["../../bad"], "taxonomy_id": None},
        {"entity_type": "publication", "identifiers": ["0"], "taxonomy_id": None},
        {"max_attempts": 6},
        {"unexpected": "reject"},
    ],
)
def test_invalid_batches_are_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        batch(**overrides)


def test_worker_progress_retry_budget_and_safe_failures(session: Session) -> None:
    now = datetime(2026, 11, 7, tzinfo=UTC)
    service = ImportJobService(session)
    job = service.create(batch(max_attempts=2))
    # available_at uses wall-clock at enqueue; choose a future test clock.
    now += timedelta(days=2)

    def fail(_session: Session, _job: object, item: ImportJobItem) -> dict[str, object]:
        if item.identifier == "TP53":
            raise UpstreamUnavailableError("mock", "SECRET must never be persisted")
        raise UpstreamNotFoundError("mock", "SECRET not-found response")

    worker = ImportWorker(session, fail, clock=lambda: now, retry_seconds=60)
    assert worker.step()
    first = service.items(job.id, 1, 100).items[0]
    assert first.status == "retry_wait" and first.attempts == 1
    assert first.available_at.replace(tzinfo=UTC) == now + timedelta(seconds=60)
    assert worker.step()  # The other identifier can run while retry is waiting.
    assert not worker.step()
    now += timedelta(seconds=60)
    assert worker.step()
    assert not worker.step()
    assert service.read(job.id).status == "completed_with_errors"
    assert service.read(job.id).counts == {"failed": 2, "total": 2}
    assert "SECRET" not in service.items(job.id, 1, 100).model_dump_json()


def test_completed_import_replay_preserves_entity_identity(session: Session) -> None:
    service = ImportJobService(session)
    job = service.create(batch(identifiers=["TP53"]))

    def import_gene(database: Session, _job: object, item: ImportJobItem) -> dict[str, object]:
        return (
            GeneIngestionService(database, FakeGeneProvider())
            .import_gene(item.identifier)
            .model_dump()
        )

    worker = ImportWorker(session, import_gene)
    assert worker.step()
    assert service.read(job.id).status == "succeeded"
    second = service.create(batch(identifiers=["TP53"]))
    assert worker.step()
    assert service.items(second.id, 1, 100).items[0].result["action"] == "unchanged"
    assert session.scalar(select(func.count()).select_from(Gene)) == 1


def test_cancel_pending_and_retrying_items_without_calling_provider(session: Session) -> None:
    service = ImportJobService(session)
    job = service.create(batch())
    assert service.cancel(job.id).status == "cancelled"

    def unexpected(*_args: object) -> dict[str, object]:
        raise AssertionError("Cancelled items must never call the provider")

    assert not ImportWorker(session, unexpected).step()
    assert service.read(job.id).counts == {"cancelled": 2, "total": 2}
    assert service.cancel(job.id).status == "cancelled"


def test_recovery_honors_attempt_budget_and_cancellation(session: Session) -> None:
    service = ImportJobService(session)
    job = service.create(batch(max_attempts=1))
    item = session.scalar(select(ImportJobItem).where(ImportJobItem.job_id == job.id))
    assert item is not None
    item.status, item.attempts = "running", 1
    session.commit()
    worker = ImportWorker(session, lambda *_: {})
    worker.recover()
    session.refresh(item)
    assert item.status == "failed" and item.error_code == "worker_interrupted"
    assert service.cancel(job.id).status == "cancelled"
    assert service.read(job.id).counts == {"failed": 1, "cancelled": 1, "total": 2}


def test_import_jobs_api_is_admin_only_and_paginated(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "/api/v1/import-jobs"
    monkeypatch.setattr(
        "app.core.security.get_settings", lambda: Settings(_env_file=None, admin_api_token=None)
    )
    assert client.get(url).status_code == 503
    monkeypatch.setattr(
        "app.core.security.get_settings",
        lambda: Settings(_env_file=None, admin_api_token=SecretStr("test-only-token")),
    )
    assert client.post(url, json=batch().model_dump()).status_code == 401
    headers = {"Authorization": "Bearer test-only-token"}
    created = client.post(url, json=batch().model_dump(), headers=headers)
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    assert client.get(url, headers=headers).json()["total"] == 1
    assert client.get(f"{url}/{job_id}").status_code == 401
    assert client.get(f"{url}/{job_id}", headers=headers).json()["status"] == "queued"
    page = client.get(f"{url}/{job_id}/items?page_size=1", headers=headers).json()
    assert page["total"] == 2 and len(page["items"]) == 1
    assert client.post(f"{url}/{job_id}/cancel", headers=headers).json()["status"] == "cancelled"
    assert client.get(f"{url}/not-a-uuid", headers=headers).status_code == 422
    assert client.get(url + "?page_size=101", headers=headers).status_code == 422


def test_http_pacing_applies_to_every_request_and_retry() -> None:
    clock = [0.0]
    starts: list[float] = []

    def sleep(delay: float) -> None:
        clock[0] += delay

    def respond(_request: httpx2.Request) -> httpx2.Response:
        starts.append(clock[0])
        return httpx2.Response(503 if len(starts) == 1 else 200, json={})

    with httpx2.Client(transport=httpx2.MockTransport(respond)) as client:
        transport = RetryingJsonClient(
            client,
            provider="mock",
            max_attempts=2,
            backoff_seconds=0,
            sleeper=sleep,
            clock=lambda: clock[0],
            min_interval_seconds=0.4,
        )
        for _ in range(2):
            transport.get_json("https://example.test", not_found_message="missing")
    assert starts == [0.0, 0.4, 0.8]


@pytest.mark.parametrize(
    "entity_type,identifier",
    [
        ("gene", "TP53"),
        ("protein", "P04637"),
        ("publication", "123456"),
    ],
)
def test_provider_dispatch_reuses_existing_provenance_importers(
    session: Session, monkeypatch: pytest.MonkeyPatch, entity_type: str, identifier: str
) -> None:
    from unittest.mock import Mock

    from app.ingestion.job_provider import ProviderImporter
    from tests.test_ingestion import FakeProteinProvider
    from tests.test_publications import publication

    monkeypatch.setattr(
        "app.ingestion.job_provider.NcbiGeneAdapter", lambda *a, **kw: FakeGeneProvider()
    )
    monkeypatch.setattr(
        "app.ingestion.job_provider.UniProtAdapter", lambda *a, **kw: FakeProteinProvider()
    )
    citation_provider = Mock()
    citation_provider.fetch_publication.return_value = publication()
    monkeypatch.setattr(
        "app.ingestion.job_provider.PubMedAdapter", lambda *a, **kw: citation_provider
    )
    service = ImportJobService(session)
    job = service.create(
        ImportJobCreate.model_validate(
            {
                "entity_type": entity_type,
                "identifiers": [identifier],
                "taxonomy_id": "9606" if entity_type == "gene" else None,
            }
        )
    )
    with httpx2.Client(
        transport=httpx2.MockTransport(lambda _: pytest.fail("No live HTTP"))
    ) as client:
        worker = ImportWorker(session, ProviderImporter(Settings(_env_file=None), client))
        assert worker.step()
    item = service.items(job.id, 1, 100).items[0]
    assert item.status == "succeeded"
    assert item.result is not None and item.result["action"] == "created"


def test_rate_limit_retry_after_is_persisted_without_multiplying_attempts(session: Session) -> None:
    from app.ingestion.job_provider import ProviderImporter

    service = ImportJobService(session)
    job = service.create(batch())
    now = datetime.now(UTC) + timedelta(days=1)
    with httpx2.Client(
        transport=httpx2.MockTransport(
            lambda _: httpx2.Response(429, headers={"Retry-After": "300"})
        )
    ) as client:
        worker = ImportWorker(
            session,
            ProviderImporter(Settings(_env_file=None, ncbi_email="test@example.org"), client),
            clock=lambda: now,
        )
        assert worker.step()
    item = service.items(job.id, 1, 100).items[0]
    assert item.attempts == 1 and item.status == "retry_wait"
    assert item.available_at.replace(tzinfo=UTC) == now + timedelta(seconds=300)


def test_database_errors_abort_instead_of_running_without_worker_lock(session: Session) -> None:
    from sqlalchemy.exc import OperationalError

    ImportJobService(session).create(batch())

    def broken_database(*_args: object) -> dict[str, object]:
        raise OperationalError("test", {}, RuntimeError("connection lost"))

    with pytest.raises(OperationalError):
        ImportWorker(session, broken_database).step()
