"""Single database-scoped worker; PostgreSQL is the durable queue and lock owner."""

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ingestion.services import IngestionPersistenceError
from app.integrations.errors import (
    IntegrationError,
    UpstreamRateLimitError,
    UpstreamUnavailableError,
)
from app.models.import_job import ImportJob, ImportJobItem
from app.services.errors import ConflictError
from app.services.import_jobs import ImportJobService

logger = logging.getLogger(__name__)
WORKER_LOCK = 724018
Importer = Callable[[Session, ImportJob, ImportJobItem], dict[str, object]]


class ImportWorker:
    """Methods require exclusive ownership of WORKER_LOCK in production."""

    def __init__(
        self,
        session: Session,
        importer: Importer,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        retry_seconds: float = 60,
    ) -> None:
        self.session = session
        self.importer = importer
        self.clock = clock
        self.retry_seconds = retry_seconds
        self.jobs = ImportJobService(session)

    def recover(self) -> None:
        # Only call after acquiring the singleton lock. A crashed attempt may
        # already have committed its entity; replay uses idempotent importers.
        items = self.session.scalars(
            select(ImportJobItem).where(ImportJobItem.status == "running")
        ).all()
        for item in items:
            job = self.jobs.get(item.job_id, lock=True)
            if job.cancel_requested:
                item.status = "cancelled"
            elif item.attempts < job.max_attempts:
                item.status = "retry_wait"
                item.available_at = self.clock() + timedelta(seconds=self.retry_seconds)
            else:
                item.status = "failed"
            item.error_code = "worker_interrupted"
            self.jobs.refresh_status(job)
            self.session.commit()

    def step(self) -> bool:
        candidate = self.session.scalar(
            select(ImportJobItem.id)
            .join(ImportJob)
            .where(
                ImportJobItem.status.in_(["pending", "retry_wait"]),
                ImportJobItem.available_at <= self.clock(),
                ImportJob.cancel_requested.is_(False),
            )
            .order_by(ImportJobItem.available_at, ImportJobItem.id)
            .limit(1)
        )
        if candidate is None:
            self.session.rollback()
            return False
        item = self.session.get(ImportJobItem, candidate)
        assert item is not None
        job = self.jobs.get(item.job_id, lock=True)
        # The cancellation API can win the job lock after the candidate SELECT.
        self.session.refresh(item)
        if job.cancel_requested or item.status not in {"pending", "retry_wait"}:
            self.session.rollback()
            return True
        item.status = "running"
        item.attempts += 1
        item.error_code = None
        job.status = "running"
        self.session.commit()
        job_id, item_id = job.id, item.id
        error_code: str | None = None
        retryable = False
        retry_after = 0.0
        result: dict[str, object] | None = None
        try:
            result = self.importer(self.session, job, item)
        except (UpstreamUnavailableError, UpstreamRateLimitError) as exc:
            error_code, retryable = exc.code, True
            if isinstance(exc, UpstreamRateLimitError):
                retry_after = exc.retry_after_seconds or 0.0
        except IntegrationError as exc:
            error_code = exc.code
        except (IngestionPersistenceError, ConflictError):
            error_code = "ingestion_conflict"
        except ValueError:
            error_code = "invalid_record"
        except SQLAlchemyError:
            # Never reconnect and continue after losing the lock-owning connection.
            raise
        except Exception:
            # Never store upstream bodies, exception text, URLs or credentials.
            error_code = "unexpected_import_error"
        self.session.rollback()
        job = self.jobs.get(job_id, lock=True)
        item = self.session.get(ImportJobItem, item_id, populate_existing=True)
        assert item is not None
        item.error_code = error_code
        if error_code is None:
            item.status, item.result = "succeeded", result
        elif job.cancel_requested:
            item.status = "cancelled"
        elif retryable and item.attempts < job.max_attempts:
            item.status = "retry_wait"
            delay = max(
                min(self.retry_seconds * 2 ** (item.attempts - 1), 3600),
                min(retry_after, 86400),
            )
            item.available_at = self.clock() + timedelta(seconds=delay)
        else:
            item.status = "failed"
        self.jobs.refresh_status(job)
        self.session.commit()
        logger.info("Import item %s finished with status %s", item.id, item.status)
        return True


def run_worker(
    engine: Engine,
    importer: Importer,
    *,
    once: bool = False,
    poll_seconds: float = 2,
    retry_seconds: float = 60,
    stopping: Callable[[], bool] = lambda: False,
) -> bool:
    if engine.dialect.name != "postgresql":
        raise ValueError("The durable import worker requires PostgreSQL.")
    # All queue operations AND entity imports use this same connection. A lost
    # connection aborts the worker instead of continuing without its session lock.
    with engine.connect() as connection:
        acquired = connection.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": WORKER_LOCK}
        )
        connection.commit()
        if not acquired:
            return False
        try:
            with Session(bind=connection, expire_on_commit=False) as session:
                worker = ImportWorker(session, importer, retry_seconds=retry_seconds)
                worker.recover()
                while not stopping():
                    processed = worker.step()
                    if once:
                        break
                    if not processed:
                        time.sleep(poll_seconds)
        finally:
            if not connection.invalidated:
                connection.rollback()
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": WORKER_LOCK})
                connection.commit()
    return True
