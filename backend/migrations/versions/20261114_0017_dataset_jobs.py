"""Allow bounded dataset jobs in the existing durable queue."""

import sqlalchemy as sa
from alembic import op

revision = "20261114_0017"
down_revision = "20261112_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_import_jobs_entity_type"), "import_jobs", type_="check")
    op.create_check_constraint(
        op.f("ck_import_jobs_entity_type"),
        "import_jobs",
        "entity_type IN ('gene', 'protein', 'publication', 'dataset')",
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text("SELECT count(*) FROM import_jobs WHERE entity_type='dataset'")
    ):
        raise RuntimeError("Dataset jobs exist; retain additive queue compatibility.")
    op.drop_constraint(op.f("ck_import_jobs_entity_type"), "import_jobs", type_="check")
    op.create_check_constraint(
        op.f("ck_import_jobs_entity_type"),
        "import_jobs",
        "entity_type IN ('gene', 'protein', 'publication')",
    )
