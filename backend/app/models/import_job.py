from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.types import BIGINT_PK


class ImportJob(TimestampMixin, Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('gene', 'protein', 'publication', 'dataset')", name="entity_type"
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'completed_with_errors', 'cancelled')",
            name="status",
        ),
        CheckConstraint("max_attempts BETWEEN 1 AND 5", name="max_attempts"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    taxonomy_id: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)


class ImportJobItem(TimestampMixin, Base):
    __tablename__ = "import_job_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'retry_wait', 'succeeded', 'failed', 'cancelled')",
            name="status",
        ),
        CheckConstraint("attempts >= 0", name="attempts"),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    result: Mapped[dict[str, object] | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(64))
