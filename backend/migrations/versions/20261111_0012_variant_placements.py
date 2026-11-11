"""Add sourced assembly-aware literal sequence variant placements."""

import sqlalchemy as sa
from alembic import op

revision = "20261111_0012"
down_revision = "20261111_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "variant_placements",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "variant_id",
            sa.BigInteger(),
            sa.ForeignKey("variants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("representation_key", sa.String(64), nullable=False),
        sa.Column("assembly_name", sa.String(128), nullable=False),
        sa.Column("assembly_accession", sa.String(32)),
        sa.Column("sequence_accession", sa.String(128), nullable=False),
        sa.Column("sequence_region", sa.String(128)),
        sa.Column("taxonomy_id", sa.String(16), nullable=False),
        sa.Column("coordinate_system", sa.String(32), nullable=False),
        sa.Column("strand", sa.String(1), nullable=False),
        sa.Column("start_position", sa.BigInteger(), nullable=False),
        sa.Column("end_position", sa.BigInteger(), nullable=False),
        sa.Column("reference_allele", sa.String(1000), nullable=False),
        sa.Column("alternate_allele", sa.String(1000), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("source_release", sa.String(128), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "variant_id",
            "representation_key",
            "source",
            "source_identifier",
            "source_release",
            name="uq_variant_placement_assertion",
        ),
        sa.CheckConstraint(
            "start_position >= 1 AND end_position >= start_position", name="coordinate_order"
        ),
        sa.CheckConstraint(
            "coordinate_system = 'one_based_closed'", name="coordinate_system_value"
        ),
        sa.CheckConstraint("strand = '+'", name="strand_value"),
        sa.CheckConstraint(
            "length(reference_allele) BETWEEN 1 AND 1000 "
            "AND length(alternate_allele) BETWEEN 1 AND 1000",
            name="allele_length",
        ),
        sa.CheckConstraint(
            "end_position - start_position + 1 = length(reference_allele)", name="reference_span"
        ),
        sa.CheckConstraint("reference_allele <> alternate_allele", name="alleles_differ"),
    )
    op.create_index("ix_variant_placements_variant_id", "variant_placements", ["variant_id"])
    op.create_index("ix_variant_placements_source", "variant_placements", ["source"])


def downgrade() -> None:
    op.drop_table("variant_placements")
