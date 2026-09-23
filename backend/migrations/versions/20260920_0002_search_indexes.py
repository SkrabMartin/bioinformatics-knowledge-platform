"""Add PostgreSQL search indexes.

Revision ID: 20260920_0002
Revises: 20260920_0001
Create Date: 2026-09-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260920_0002"
down_revision: str | None = "20260920_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute("CREATE INDEX ix_genes_symbol_trgm ON genes USING gin (symbol gin_trgm_ops)")
    op.execute("CREATE INDEX ix_genes_name_trgm ON genes USING gin (name gin_trgm_ops)")
    op.execute(
        "CREATE INDEX ix_genes_ncbi_gene_id_trgm ON genes USING gin (ncbi_gene_id gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_genes_ensembl_gene_id_trgm "
        "ON genes USING gin (ensembl_gene_id gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_genes_search_document ON genes USING gin "
        "(to_tsvector('simple', coalesce(symbol, '') || ' ' || coalesce(name, '') || ' ' || "
        "coalesce(description, '') || ' ' || coalesce(ncbi_gene_id, '') || ' ' || "
        "coalesce(ensembl_gene_id, '')))"
    )

    op.execute(
        "CREATE INDEX ix_proteins_accession_trgm ON proteins USING gin (accession gin_trgm_ops)"
    )
    op.execute("CREATE INDEX ix_proteins_name_trgm ON proteins USING gin (name gin_trgm_ops)")
    op.execute(
        "CREATE INDEX ix_proteins_search_document ON proteins USING gin "
        "(to_tsvector('simple', coalesce(accession, '') || ' ' || coalesce(name, '') || ' ' || "
        "coalesce(function, '')))"
    )

    op.execute(
        "CREATE INDEX ix_organisms_scientific_name_trgm "
        "ON organisms USING gin (scientific_name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_organisms_common_name_trgm "
        "ON organisms USING gin (common_name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_organisms_taxonomy_id_trgm "
        "ON organisms USING gin (taxonomy_id gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_organisms_search_document ON organisms USING gin "
        "(to_tsvector('simple', coalesce(scientific_name, '') || ' ' || "
        "coalesce(common_name, '') || ' ' || coalesce(taxonomy_id, '')))"
    )


def downgrade() -> None:
    op.drop_index("ix_organisms_search_document", table_name="organisms")
    op.drop_index("ix_organisms_taxonomy_id_trgm", table_name="organisms")
    op.drop_index("ix_organisms_common_name_trgm", table_name="organisms")
    op.drop_index("ix_organisms_scientific_name_trgm", table_name="organisms")
    op.drop_index("ix_proteins_search_document", table_name="proteins")
    op.drop_index("ix_proteins_name_trgm", table_name="proteins")
    op.drop_index("ix_proteins_accession_trgm", table_name="proteins")
    op.drop_index("ix_genes_search_document", table_name="genes")
    op.drop_index("ix_genes_ensembl_gene_id_trgm", table_name="genes")
    op.drop_index("ix_genes_ncbi_gene_id_trgm", table_name="genes")
    op.drop_index("ix_genes_name_trgm", table_name="genes")
    op.drop_index("ix_genes_symbol_trgm", table_name="genes")
    # pg_trgm may be shared by other schemas/applications, so downgrade does not drop it.
