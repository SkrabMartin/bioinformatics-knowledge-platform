"""Queue concurrency and crash replay on an explicitly disposable migrated database."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.orm import Session

from app.ingestion.services import GeneIngestionService
from app.ingestion.worker import WORKER_LOCK, run_worker
from app.models import Gene, GeneExternalIdentifier, GeneIdentifierEvidence, Organism
from app.models.import_job import ImportJob, ImportJobItem
from app.schemas.import_job import ImportJobCreate
from app.services.import_jobs import ImportJobService
from tests.test_ingestion import FakeGeneProvider


class SimulatedProcessExit(BaseException):
    pass


def test_postgresql_worker_lock_crash_replay_and_inflight_cancellation() -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set BKP_TEST_POSTGRES_URL to an isolated migrated PostgreSQL database.")
    engine = create_engine(url)
    ids: list[str] = []
    gene_id: int | None = None
    organism_id: int | None = None
    try:
        with Session(engine, expire_on_commit=False) as session:
            service = ImportJobService(session)
            payload = ImportJobCreate(
                entity_type="gene",
                identifiers=["TP53"],
                taxonomy_id="9606",
                idempotency_key=f"test-{uuid4()}",
            )
            job = service.create(payload)
            ids.append(job.id)
            session.rollback()
        with engine.connect() as owner:
            owner.execute(text("SELECT pg_advisory_lock(:key)"), {"key": WORKER_LOCK})
            owner.commit()
            assert not run_worker(engine, lambda *_: {}, once=True)
            owner.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": WORKER_LOCK})
            owner.commit()

        def commit_then_crash(
            session: Session, _job: ImportJob, item: ImportJobItem
        ) -> dict[str, object]:
            nonlocal gene_id, organism_id
            result = GeneIngestionService(session, FakeGeneProvider()).import_gene(item.identifier)
            gene_id = result.entity_id
            gene = session.get(Gene, gene_id)
            assert gene is not None
            organism_id = gene.organism_id
            raise SimulatedProcessExit()

        with pytest.raises(SimulatedProcessExit):
            run_worker(engine, commit_then_crash, once=True, retry_seconds=0)

        def import_again(
            session: Session, _job: ImportJob, item: ImportJobItem
        ) -> dict[str, object]:
            return (
                GeneIngestionService(session, FakeGeneProvider())
                .import_gene(item.identifier)
                .model_dump()
            )

        assert run_worker(engine, import_again, once=True, retry_seconds=0)
        with Session(engine, expire_on_commit=False) as session:
            service = ImportJobService(session)
            assert service.read(job.id).status == "succeeded"
            item = service.items(job.id, 1, 100).items[0]
            assert item.attempts == 2
            assert item.result is not None and item.result["action"] == "unchanged"
            assert session.scalar(select(func.count()).select_from(Gene)) == 1
            second = service.create(
                ImportJobCreate(
                    entity_type="gene", identifiers=["TP53", "BRCA1"], taxonomy_id="9606"
                )
            )
            ids.append(second.id)
            session.rollback()

        def cancel_during_import(
            _session: Session, job: ImportJob, _item: ImportJobItem
        ) -> dict[str, object]:
            # Different connection must not block behind an open worker transaction.
            with Session(engine) as other:
                other.execute(text("SET LOCAL lock_timeout = '1000ms'"))
                assert ImportJobService(other).cancel(job.id).cancel_requested
            assert not run_worker(engine, lambda *_: {}, once=True)
            return {"action": "unchanged", "entity_id": gene_id}

        assert run_worker(engine, cancel_during_import, once=True)
        with Session(engine) as session:
            final = ImportJobService(session).read(second.id)
            assert final.status == "cancelled"
            assert final.counts == {"succeeded": 1, "cancelled": 1, "total": 2}
    finally:
        with Session(engine) as session:
            session.execute(delete(ImportJobItem).where(ImportJobItem.job_id.in_(ids)))
            session.execute(delete(ImportJob).where(ImportJob.id.in_(ids)))
            if gene_id is not None:
                identifiers = select(GeneExternalIdentifier.id).where(
                    GeneExternalIdentifier.gene_id == gene_id
                )
                session.execute(
                    delete(GeneIdentifierEvidence).where(
                        GeneIdentifierEvidence.identifier_id.in_(identifiers)
                    )
                )
                session.execute(
                    delete(GeneExternalIdentifier).where(GeneExternalIdentifier.gene_id == gene_id)
                )
                session.execute(delete(Gene).where(Gene.id == gene_id))
            if organism_id is not None:
                session.execute(delete(Organism).where(Organism.id == organism_id))
            session.commit()
        engine.dispose()
