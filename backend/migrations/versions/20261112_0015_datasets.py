"""Add sourced GEO Series dataset discovery metadata."""

import sqlalchemy as sa
from alembic import op

revision = "20261112_0015"
down_revision = "20261112_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("repository", sa.String(32), nullable=False),
        sa.Column("accession", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("experiment_types", sa.JSON(), nullable=False),
        sa.Column("organism_names", sa.JSON(), nullable=False),
        sa.Column("taxonomy_ids", sa.JSON(), nullable=False),
        sa.Column("platform_accessions", sa.JSON(), nullable=False),
        sa.Column("publication_pmids", sa.JSON(), nullable=False),
        sa.Column("sample_count", sa.Integer()),
        sa.Column("source_updated_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("repository", "accession", name="uq_datasets_repository_accession"),
        sa.CheckConstraint("repository = 'GEO'", name="repository_value"),
        sa.CheckConstraint(
            "sample_count IS NULL OR sample_count BETWEEN 0 AND 100000", name="sample_count_range"
        ),
    )
    op.create_index("ix_datasets_source", "datasets", ["source"])


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM datasets")):
        raise RuntimeError("Refusing to discard dataset records; retain additive schema.")
    op.drop_table("datasets")
