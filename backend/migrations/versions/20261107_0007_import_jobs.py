"""Add durable bounded import jobs without changing biological records."""

import sqlalchemy as sa
from alembic import op

revision = "20261107_0007"
down_revision = "20261023_0006"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(16), nullable=False),
        sa.Column("taxonomy_id", sa.String(16)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), unique=True),
        *timestamps(),
        sa.CheckConstraint("entity_type IN ('gene', 'protein', 'publication')", name="entity_type"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'completed_with_errors', 'cancelled')",
            name="status",
        ),
        sa.CheckConstraint("max_attempts BETWEEN 1 AND 5", name="max_attempts"),
    )
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"])
    op.create_table(
        "import_job_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("import_jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("error_code", sa.String(64)),
        *timestamps(),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'retry_wait', 'succeeded', 'failed', 'cancelled')",
            name="status",
        ),
        sa.CheckConstraint("attempts >= 0", name="attempts"),
    )
    for field in ("job_id", "status", "available_at"):
        op.create_index(f"ix_import_job_items_{field}", "import_job_items", [field])


def downgrade() -> None:
    op.drop_table("import_job_items")
    op.drop_table("import_jobs")
