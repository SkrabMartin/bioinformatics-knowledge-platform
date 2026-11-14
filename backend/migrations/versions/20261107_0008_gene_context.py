"""Add source-backed gene aliases and reference sequence placements."""

import sqlalchemy as sa
from alembic import op

revision = "20261107_0008"
down_revision = "20261107_0007"
branch_labels = None
depends_on = None


def provenance() -> list[sa.Column]:
    return [
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "gene_aliases",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "gene_id",
            sa.BigInteger(),
            sa.ForeignKey("genes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(64), nullable=False),
        *provenance(),
        sa.UniqueConstraint("gene_id", "source", "alias", name="uq_gene_aliases_source"),
        sa.CheckConstraint("length(alias) > 0", name="alias_nonempty"),
    )
    op.create_index("ix_gene_aliases_gene_id", "gene_aliases", ["gene_id"])
    op.create_index("ix_gene_aliases_source", "gene_aliases", ["source"])
    op.create_index(
        "ix_gene_aliases_alias_trgm",
        "gene_aliases",
        ["alias"],
        postgresql_using="gin",
        postgresql_ops={"alias": "gin_trgm_ops"},
    )
    op.create_table(
        "gene_genomic_locations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "gene_id",
            sa.BigInteger(),
            sa.ForeignKey("genes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence_accession", sa.String(64), nullable=False),
        sa.Column("chromosome", sa.String(64)),
        sa.Column("start_position", sa.BigInteger(), nullable=False),
        sa.Column("end_position", sa.BigInteger(), nullable=False),
        sa.Column("strand", sa.String(1), nullable=False),
        *provenance(),
        sa.UniqueConstraint(
            "gene_id",
            "source",
            "sequence_accession",
            "start_position",
            "end_position",
            "strand",
            name="uq_gene_genomic_locations_source",
        ),
        sa.CheckConstraint("start_position >= 1", name="start_positive"),
        sa.CheckConstraint("end_position >= start_position", name="position_order"),
        sa.CheckConstraint("strand IN ('+', '-')", name="strand_value"),
        sa.CheckConstraint("length(sequence_accession) > 0", name="sequence_nonempty"),
    )
    for field in ("gene_id", "source", "sequence_accession"):
        op.create_index(f"ix_gene_genomic_locations_{field}", "gene_genomic_locations", [field])


def downgrade() -> None:
    op.drop_table("gene_genomic_locations")
    op.drop_table("gene_aliases")
