"""Add source-backed Ensembl transcripts without changing existing biological tables."""

import sqlalchemy as sa
from alembic import op

revision = "20261107_0009"
down_revision = "20261107_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transcripts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "gene_id",
            sa.BigInteger(),
            sa.ForeignKey("genes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("ensembl_transcript_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer()),
        sa.Column("name", sa.String(255)),
        sa.Column("biotype", sa.String(128)),
        sa.Column("assembly_name", sa.String(128), nullable=False),
        sa.Column("sequence_region", sa.String(128), nullable=False),
        sa.Column("start_position", sa.BigInteger(), nullable=False),
        sa.Column("end_position", sa.BigInteger(), nullable=False),
        sa.Column("strand", sa.String(1), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("source_release", sa.String(16), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("ensembl_transcript_id", name="uq_transcripts_ensembl_id"),
        sa.CheckConstraint("start_position >= 1", name="start_positive"),
        sa.CheckConstraint("end_position >= start_position", name="position_order"),
        sa.CheckConstraint("strand IN ('+', '-')", name="strand_value"),
        sa.CheckConstraint("version IS NULL OR version >= 1", name="version_positive"),
        sa.CheckConstraint("source = 'Ensembl'", name="source_value"),
    )
    for field in ("gene_id", "source"):
        op.create_index(f"ix_transcripts_{field}", "transcripts", [field])


def downgrade() -> None:
    op.drop_table("transcripts")
