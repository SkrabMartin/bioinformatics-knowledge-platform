"""Add first-observed sourced GEO dataset citation links."""

import sqlalchemy as sa
from alembic import op

revision = "20261112_0016"
down_revision = "20261112_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_publications",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.BigInteger(),
            sa.ForeignKey("datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "publication_id",
            sa.BigInteger(),
            sa.ForeignKey("publications.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reported_pmid", sa.String(32), nullable=False),
        sa.Column("source_record_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column("evidence_text", sa.Text()),
        sa.Column("evidence_kind", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "dataset_id", "publication_id", name="uq_dataset_publications_identity"
        ),
        sa.CheckConstraint("evidence_kind = 'structured_metadata'", name="evidence_kind"),
    )
    for field in ("dataset_id", "publication_id", "source"):
        op.create_index(f"ix_dataset_publications_{field}", "dataset_publications", [field])


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM dataset_publications")):
        raise RuntimeError("Refusing to discard sourced dataset citations; retain additive schema.")
    op.drop_table("dataset_publications")
