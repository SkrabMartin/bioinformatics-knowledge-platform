"""Synthetic metadata through the durable worker; never live provider calls."""

from datetime import UTC, datetime, timedelta

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.job_provider import ProviderImporter
from app.ingestion.worker import ImportWorker
from app.integrations.geo import parse_geo_series
from app.models import Dataset, DatasetPublication, Publication
from app.schemas.import_job import ImportJobCreate
from app.services.datasets import DatasetService
from app.services.import_jobs import ImportJobService
from app.services.import_status import import_status
from tests.test_datasets import SOFT


def payload(**updates):
    return ImportJobCreate.model_validate(
        {"entity_type": "dataset", "identifiers": ["GSE999999"], **updates}
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"identifiers": ["GSE0"]},
        {"identifiers": ["gse999999"]},
        {"identifiers": ["https://example.test/GSE999999"]},
        {"taxonomy_id": "9606"},
    ],
)
def test_dataset_queue_rejects_invalid_scope(updates):
    with pytest.raises(ValidationError):
        payload(**updates)


def test_dataset_worker_import_replay_and_aggregate_privacy(session: Session):
    service = ImportJobService(session)
    data = payload(identifiers=[" GSE999999 ", "GSE999999"], idempotency_key="PRIVATE-KEY")
    job = service.create(data)
    assert service.create(data).id == job.id and job.counts["total"] == 1
    calls = []

    def respond(request):
        calls.append(request)
        assert request.url.params["targ"] == "self" and request.url.params["view"] == "brief"
        return httpx2.Response(200, text=SOFT)

    with httpx2.Client(transport=httpx2.MockTransport(respond)) as client:
        worker = ImportWorker(
            session,
            ProviderImporter(
                Settings(_env_file=None, import_request_interval_seconds=0.34), client
            ),
        )
        assert worker.step()
        result = service.items(job.id, 1, 100).items[0].result
        assert result["entity_type"] == "dataset" and result["action"] == "created"
        other = service.create(payload())
        assert worker.step()
        assert service.items(other.id, 1, 100).items[0].result["action"] == "unchanged"
    assert len(calls) == 2
    assert session.scalar(select(func.count()).select_from(Dataset)) == 1
    assert session.scalar(select(func.count()).select_from(Publication)) == 0
    assert session.scalar(select(func.count()).select_from(DatasetPublication)) == 0
    report = import_status(session)
    row = next(r for r in report.activity if r.entity_type == "dataset")
    assert row.jobs["succeeded"] == row.items["succeeded"] == 2
    assert row.last_activity_at is not None and report.worker_status == "unknown"
    text = report.model_dump_json()
    assert all(
        secret not in text
        for secret in ["PRIVATE-KEY", job.id, "GSE999999", "source_url", "error_code", "identifier"]
    )


def test_dataset_conflict_fails_without_retry_or_overwrite(session: Session):
    record, _ = DatasetService(session).save(
        parse_geo_series(SOFT.replace("Jan 02 2020", "Jan 02 2021"), "GSE999999")
    )
    job = ImportJobService(session).create(payload())
    with httpx2.Client(
        transport=httpx2.MockTransport(lambda _: httpx2.Response(200, text=SOFT))
    ) as client:
        worker = ImportWorker(session, ProviderImporter(Settings(_env_file=None), client))
        assert worker.step() and not worker.step()
    item = ImportJobService(session).items(job.id, 1, 100).items[0]
    assert (
        item.status == "failed" and item.error_code == "ingestion_conflict" and item.attempts == 1
    )
    assert DatasetService(session).get(record.id).source_updated_date.year == 2021


def test_dataset_unavailable_uses_queue_attempt_budget(session: Session):
    service = ImportJobService(session)
    job = service.create(payload(max_attempts=2))
    now = datetime.now(UTC) + timedelta(seconds=5)
    calls = []

    def unavailable(request):
        calls.append(request)
        return httpx2.Response(503, text="PRIVATE-PROVIDER-BODY")

    with httpx2.Client(transport=httpx2.MockTransport(unavailable)) as client:
        worker = ImportWorker(
            session,
            ProviderImporter(
                Settings(_env_file=None, import_request_interval_seconds=0.34), client
            ),
            clock=lambda: now,
            retry_seconds=10,
        )
        assert worker.step() and not worker.step()
        assert service.items(job.id, 1, 100).items[0].status == "retry_wait"
        now += timedelta(seconds=10)
        assert worker.step() and not worker.step()
    item = service.items(job.id, 1, 100).items[0]
    assert item.status == "failed" and item.attempts == 2 and len(calls) == 2
    assert "PRIVATE" not in item.model_dump_json()


def test_empty_status_and_cancelled_history_have_honest_counts(session: Session):
    assert len(import_status(session).activity) == 4
    assert all(
        row.jobs["total"] == row.items["total"] == 0 for row in import_status(session).activity
    )
    service = ImportJobService(session)
    job = service.create(payload())
    service.cancel(job.id)
    report = import_status(session)
    row = next(r for r in report.activity if r.entity_type == "dataset")
    assert row.jobs["cancelled"] == row.items["cancelled"] == 1
    assert report.worker_status == "unknown"


def test_public_status_is_read_only_while_job_details_stay_protected(client: TestClient):
    r = client.get("/api/v1/import-status")
    assert r.status_code == 200 and r.json()["worker_status"] == "unknown"
    assert len(r.json()["activity"]) == 4
    assert client.get("/api/v1/import-jobs").status_code in {401, 503}
    assert client.post("/api/v1/import-jobs", json=payload().model_dump()).status_code in {401, 503}
    assert client.post("/api/v1/import-status").status_code == 405
