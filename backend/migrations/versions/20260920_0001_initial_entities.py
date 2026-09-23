"""Create organism, gene, and protein tables.

Revision ID: 20260920_0001
Revises:
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260920_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def provenance_columns() -> list[sa.Column]:
    return [
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_identifier", sa.String(length=255), nullable=True),
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


def upgrade() -> None:
    op.create_table(
        "organisms",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("scientific_name", sa.String(length=255), nullable=False),
        sa.Column("common_name", sa.String(length=255), nullable=True),
        sa.Column("taxonomy_id", sa.String(length=32), nullable=True),
        *provenance_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_organisms"),
        sa.UniqueConstraint("taxonomy_id", name="uq_organisms_taxonomy_id"),
    )
    op.create_index("ix_organisms_scientific_name", "organisms", ["scientific_name"])
    op.create_index("ix_organisms_source", "organisms", ["source"])
    op.create_index("ix_organisms_taxonomy_id", "organisms", ["taxonomy_id"])

    op.create_table(
        "genes",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("organism_id", sa.BigInteger(), nullable=False),
        sa.Column("chromosome", sa.String(length=64), nullable=True),
        sa.Column("start_position", sa.BigInteger(), nullable=True),
        sa.Column("end_position", sa.BigInteger(), nullable=True),
        sa.Column("strand", sa.String(length=1), nullable=True),
        sa.Column("ncbi_gene_id", sa.String(length=64), nullable=True),
        sa.Column("ensembl_gene_id", sa.String(length=64), nullable=True),
        *provenance_columns(),
        sa.CheckConstraint(
            "start_position IS NULL OR start_position >= 0", name="ck_genes_start_nonnegative"
        ),
        sa.CheckConstraint(
            "end_position IS NULL OR end_position >= 0", name="ck_genes_end_nonnegative"
        ),
        sa.CheckConstraint(
            "start_position IS NULL OR end_position IS NULL OR end_position >= start_position",
            name="ck_genes_position_order",
        ),
        sa.CheckConstraint("strand IS NULL OR strand IN ('+', '-')", name="ck_genes_strand_value"),
        sa.ForeignKeyConstraint(
            ["organism_id"],
            ["organisms.id"],
            name="fk_genes_organism_id_organisms",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_genes"),
        sa.UniqueConstraint("ensembl_gene_id", name="uq_genes_ensembl_gene_id"),
        sa.UniqueConstraint("ncbi_gene_id", name="uq_genes_ncbi_gene_id"),
        sa.UniqueConstraint("organism_id", "symbol", name="uq_genes_organism_symbol"),
    )
    op.create_index("ix_genes_ensembl_gene_id", "genes", ["ensembl_gene_id"])
    op.create_index("ix_genes_ncbi_gene_id", "genes", ["ncbi_gene_id"])
    op.create_index("ix_genes_organism_id", "genes", ["organism_id"])
    op.create_index("ix_genes_organism_symbol", "genes", ["organism_id", "symbol"])
    op.create_index("ix_genes_source", "genes", ["source"])

    op.create_table(
        "proteins",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("accession", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("gene_id", sa.BigInteger(), nullable=True),
        sa.Column("organism_id", sa.BigInteger(), nullable=False),
        sa.Column("function", sa.Text(), nullable=True),
        sa.Column("sequence_length", sa.Integer(), nullable=True),
        *provenance_columns(),
        sa.CheckConstraint(
            "sequence_length IS NULL OR sequence_length > 0",
            name="ck_proteins_sequence_length_positive",
        ),
        sa.ForeignKeyConstraint(
            ["gene_id"], ["genes.id"], name="fk_proteins_gene_id_genes", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["organism_id"],
            ["organisms.id"],
            name="fk_proteins_organism_id_organisms",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_proteins"),
        sa.UniqueConstraint("accession", name="uq_proteins_accession"),
    )
    op.create_index("ix_proteins_accession", "proteins", ["accession"])
    op.create_index("ix_proteins_gene_id", "proteins", ["gene_id"])
    op.create_index("ix_proteins_organism_id", "proteins", ["organism_id"])
    op.create_index("ix_proteins_source", "proteins", ["source"])


def downgrade() -> None:
    op.drop_table("proteins")
    op.drop_table("genes")
    op.drop_table("organisms")
