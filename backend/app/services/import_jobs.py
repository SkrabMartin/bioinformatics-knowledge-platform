from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.import_job import ImportJob, ImportJobItem
from app.schemas.common import Page
from app.schemas.import_job import ImportJobCreate, ImportJobItemRead, ImportJobRead
from app.services.errors import ConflictError, NotFoundError

TERMINAL_ITEMS = {"succeeded", "failed", "cancelled"}


class ImportJobService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, payload: ImportJobCreate) -> ImportJobRead:
        existing = self._by_key(payload.idempotency_key)
        if existing is not None:
            return self._replay(existing, payload)
        job = ImportJob(
            entity_type=payload.entity_type,
            taxonomy_id=payload.taxonomy_id,
            max_attempts=payload.max_attempts,
            idempotency_key=payload.idempotency_key,
        )
        self.session.add(job)
        try:
            self.session.flush()
            self.session.add_all(
                ImportJobItem(job_id=job.id, identifier=identifier, available_at=datetime.now(UTC))
                for identifier in payload.identifiers
            )
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self._by_key(payload.idempotency_key)
            if existing is None:
                raise
            return self._replay(existing, payload)
        return self.read(job.id)

    def _by_key(self, key: str | None) -> ImportJob | None:
        if key is None:
            return None
        return self.session.scalar(select(ImportJob).where(ImportJob.idempotency_key == key))

    def _replay(self, job: ImportJob, payload: ImportJobCreate) -> ImportJobRead:
        identifiers = list(
            self.session.scalars(
                select(ImportJobItem.identifier)
                .where(ImportJobItem.job_id == job.id)
                .order_by(ImportJobItem.id)
            )
        )
        if (
            job.entity_type != payload.entity_type
            or job.taxonomy_id != payload.taxonomy_id
            or job.max_attempts != payload.max_attempts
            or identifiers != payload.identifiers
        ):
            raise ConflictError("Idempotency key already belongs to a different batch.")
        return self.read(job.id)

    def get(self, job_id: str, *, lock: bool = False) -> ImportJob:
        query = select(ImportJob).where(ImportJob.id == job_id)
        if lock:
            query = query.with_for_update()
        job = self.session.scalar(query.execution_options(populate_existing=True))
        if job is None:
            raise NotFoundError("Import job was not found.")
        return job

    def read(self, job_id: str) -> ImportJobRead:
        job = self.get(job_id)
        counts: dict[str, int] = {
            status: count
            for status, count in self.session.execute(
                select(ImportJobItem.status, func.count())
                .where(ImportJobItem.job_id == job_id)
                .group_by(ImportJobItem.status)
            ).all()
        }
        return ImportJobRead(
            **{
                field: getattr(job, field)
                for field in ImportJobRead.model_fields
                if field != "counts"
            },
            counts={**counts, "total": sum(counts.values())},
        )

    def browse(self, page: int, page_size: int) -> Page[ImportJobRead]:
        total = self.session.scalar(select(func.count()).select_from(ImportJob)) or 0
        ids = self.session.scalars(
            select(ImportJob.id)
            .order_by(ImportJob.created_at.desc(), ImportJob.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return Page(
            items=[self.read(job_id) for job_id in ids],
            page=page,
            page_size=page_size,
            total=total,
            pages=(total + page_size - 1) // page_size,
        )

    def items(self, job_id: str, page: int, page_size: int) -> Page[ImportJobItemRead]:
        self.get(job_id)
        query = select(ImportJobItem).where(ImportJobItem.job_id == job_id)
        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.session.scalars(
            query.order_by(ImportJobItem.id).offset((page - 1) * page_size).limit(page_size)
        )
        return Page(
            items=[ImportJobItemRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size,
        )

    def cancel(self, job_id: str) -> ImportJobRead:
        job = self.get(job_id, lock=True)
        if job.status in {"queued", "running"}:
            job.cancel_requested = True
            self.session.execute(
                update(ImportJobItem)
                .where(
                    ImportJobItem.job_id == job_id,
                    ImportJobItem.status.in_(["pending", "retry_wait"]),
                )
                .values(status="cancelled")
            )
            self.refresh_status(job)
            self.session.commit()
        return self.read(job_id)

    def refresh_status(self, job: ImportJob) -> None:
        self.session.flush()
        statuses = set(
            self.session.scalars(select(ImportJobItem.status).where(ImportJobItem.job_id == job.id))
        )
        if statuses <= TERMINAL_ITEMS:
            job.status = (
                "cancelled"
                if job.cancel_requested
                else "completed_with_errors"
                if "failed" in statuses
                else "succeeded"
            )
        elif "running" in statuses or statuses & TERMINAL_ITEMS or "retry_wait" in statuses:
            job.status = "running"
        else:
            job.status = "queued"
