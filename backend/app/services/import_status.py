from datetime import UTC, datetime

from sqlalchemy import func, literal, select, union_all
from sqlalchemy.orm import Session

from app.models.import_job import ImportJob, ImportJobItem
from app.schemas.import_job import ImportEntityType
from app.schemas.import_status import ImportActivity, ImportStatusRead

KINDS: tuple[ImportEntityType, ...] = ("gene", "protein", "publication", "dataset")
JOB_STATES = ("queued", "running", "succeeded", "completed_with_errors", "cancelled")
ITEM_STATES = ("pending", "running", "retry_wait", "succeeded", "failed", "cancelled")


def import_status(session: Session) -> ImportStatusRead:
    # One grouped statement: no identifiers, results, keys or provider errors are selected.
    jobs = select(
        literal("jobs").label("kind"),
        ImportJob.entity_type,
        ImportJob.status,
        func.count().label("count"),
        func.max(ImportJob.updated_at).label("last_activity"),
    ).group_by(ImportJob.entity_type, ImportJob.status)
    items = (
        select(
            literal("items").label("kind"),
            ImportJob.entity_type,
            ImportJobItem.status,
            func.count().label("count"),
            func.max(ImportJobItem.updated_at).label("last_activity"),
        )
        .join(ImportJob, ImportJob.id == ImportJobItem.job_id)
        .group_by(ImportJob.entity_type, ImportJobItem.status)
    )
    activity = {
        kind: ImportActivity(
            entity_type=kind,
            jobs=dict.fromkeys((*JOB_STATES, "total"), 0),
            items=dict.fromkeys((*ITEM_STATES, "total"), 0),
            last_activity_at=None,
        )
        for kind in KINDS
    }
    for row in session.execute(union_all(jobs, items)).mappings():
        entry = activity[row["entity_type"]]
        counts = entry.jobs if row["kind"] == "jobs" else entry.items
        counts[row["status"]] = row["count"]
        counts["total"] += row["count"]
        when = row["last_activity"]
        if when is not None:
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            if entry.last_activity_at is None or when > entry.last_activity_at:
                entry.last_activity_at = when
    return ImportStatusRead(observed_at=datetime.now(UTC), activity=list(activity.values()))
