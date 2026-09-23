"""Add diseases, variants, and typed provenance-bearing relationships.

Revision ID: 20260921_0003
Revises: 20260920_0002
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260921_0003"
down_revision: str | None = "20260920_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def provenance_columns(*, relationship: bool = False) -> list[sa.Column]:
    columns = [
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_identifier", sa.String(length=255), nullable=not relationship),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]
    if relationship:
        columns.append(sa.Column("evidence_text", sa.Text(), nullable=True))
    return columns


def upgrade() -> None:
    op.create_table(
        "diseases",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mondo_id", sa.String(length=64), nullable=True),
        sa.Column("disease_ontology_id", sa.String(length=64), nullable=True),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_diseases"),
        sa.UniqueConstraint("name", name="uq_diseases_name"),
        sa.UniqueConstraint("mondo_id", name="uq_diseases_mondo_id"),
        sa.UniqueConstraint("disease_ontology_id", name="uq_diseases_disease_ontology_id"),
    )
    for field in ("name", "mondo_id", "disease_ontology_id", "source"):
        op.create_index(f"ix_diseases_{field}", "diseases", [field])

    op.create_table(
        "variants",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("rsid", sa.String(length=64), nullable=True),
        sa.Column("hgvs", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("organism_id", sa.BigInteger(), nullable=False),
        *provenance_columns(),
        sa.CheckConstraint(
            "rsid IS NOT NULL OR hgvs IS NOT NULL", name="ck_variants_identifier_required"
        ),
        sa.ForeignKeyConstraint(
            ["organism_id"],
            ["organisms.id"],
            name="fk_variants_organism_id_organisms",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_variants"),
        sa.UniqueConstraint("rsid", name="uq_variants_rsid"),
        sa.UniqueConstraint("hgvs", name="uq_variants_hgvs"),
    )
    for field in ("rsid", "hgvs", "organism_id", "source"):
        op.create_index(f"ix_variants_{field}", "variants", [field])

    op.create_table(
        "gene_disease_associations",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("gene_id", sa.BigInteger(), nullable=False),
        sa.Column("disease_id", sa.BigInteger(), nullable=False),
        *provenance_columns(relationship=True),
        sa.ForeignKeyConstraint(
            ["gene_id"],
            ["genes.id"],
            name="fk_gene_disease_associations_gene_id_genes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["disease_id"],
            ["diseases.id"],
            name="fk_gene_disease_associations_disease_id_diseases",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gene_disease_associations"),
        sa.UniqueConstraint(
            "gene_id", "disease_id", "source", "source_identifier", name="uq_gene_disease_source"
        ),
    )
    for field in ("gene_id", "disease_id", "source"):
        op.create_index(
            f"ix_gene_disease_associations_{field}", "gene_disease_associations", [field]
        )

    op.create_table(
        "variant_gene_locations",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("variant_id", sa.BigInteger(), nullable=False),
        sa.Column("gene_id", sa.BigInteger(), nullable=False),
        *provenance_columns(relationship=True),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["variants.id"],
            name="fk_variant_gene_locations_variant_id_variants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["gene_id"],
            ["genes.id"],
            name="fk_variant_gene_locations_gene_id_genes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_variant_gene_locations"),
        sa.UniqueConstraint(
            "variant_id", "gene_id", "source", "source_identifier", name="uq_variant_gene_source"
        ),
    )
    for field in ("variant_id", "gene_id", "source"):
        op.create_index(f"ix_variant_gene_locations_{field}", "variant_gene_locations", [field])

    op.create_table(
        "variant_disease_associations",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("variant_id", sa.BigInteger(), nullable=False),
        sa.Column("disease_id", sa.BigInteger(), nullable=False),
        *provenance_columns(relationship=True),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["variants.id"],
            name="fk_variant_disease_associations_variant_id_variants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["disease_id"],
            ["diseases.id"],
            name="fk_variant_disease_associations_disease_id_diseases",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_variant_disease_associations"),
        sa.UniqueConstraint(
            "variant_id",
            "disease_id",
            "source",
            "source_identifier",
            name="uq_variant_disease_source",
        ),
    )
    for field in ("variant_id", "disease_id", "source"):
        op.create_index(
            f"ix_variant_disease_associations_{field}", "variant_disease_associations", [field]
        )

    op.create_table(
        "protein_interactions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("protein_a_id", sa.BigInteger(), nullable=False),
        sa.Column("protein_b_id", sa.BigInteger(), nullable=False),
        *provenance_columns(relationship=True),
        sa.CheckConstraint(
            "protein_a_id < protein_b_id", name="ck_protein_interactions_ordered_pair"
        ),
        sa.ForeignKeyConstraint(
            ["protein_a_id"],
            ["proteins.id"],
            name="fk_protein_interactions_protein_a_id_proteins",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["protein_b_id"],
            ["proteins.id"],
            name="fk_protein_interactions_protein_b_id_proteins",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_protein_interactions"),
        sa.UniqueConstraint(
            "protein_a_id",
            "protein_b_id",
            "source",
            "source_identifier",
            name="uq_protein_interaction_source",
        ),
    )
    for field in ("protein_a_id", "protein_b_id", "source"):
        op.create_index(f"ix_protein_interactions_{field}", "protein_interactions", [field])


def downgrade() -> None:
    for table, fields in (
        ("protein_interactions", ("source", "protein_b_id", "protein_a_id")),
        ("variant_disease_associations", ("source", "disease_id", "variant_id")),
        ("variant_gene_locations", ("source", "gene_id", "variant_id")),
        ("gene_disease_associations", ("source", "disease_id", "gene_id")),
        ("variants", ("source", "organism_id", "hgvs", "rsid")),
        ("diseases", ("source", "disease_ontology_id", "mondo_id", "name")),
    ):
        for field in fields:
            op.drop_index(f"ix_{table}_{field}", table_name=table)
        op.drop_table(table)
