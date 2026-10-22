"""Add publications and explicit literature assertions.

Revision ID: 20261022_0005
Revises: 20260921_0004
"""

import sqlalchemy as sa
from alembic import op

revision = "20261022_0005"
down_revision = "20260921_0004"
branch_labels = None
depends_on = None


def provenance(*, assertion: bool = False) -> list[sa.Column]:
    columns = [
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=not assertion),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]
    if assertion:
        columns += [
            sa.Column("evidence_text", sa.Text()),
            sa.Column("evidence_kind", sa.String(32), nullable=False),
        ]
    return columns


def upgrade() -> None:
    op.create_table(
        "publications",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("pubmed_id", sa.String(32)),
        sa.Column("doi", sa.String(255)),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text()),
        sa.Column("journal", sa.String(512)),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("publication_date", sa.String(10)),
        sa.Column("publication_date_text", sa.String(255)),
        *provenance(),
        sa.CheckConstraint("pubmed_id IS NOT NULL OR doi IS NOT NULL", name="identifier_required"),
        sa.UniqueConstraint("pubmed_id", name="uq_publications_pubmed_id"),
        sa.UniqueConstraint("doi", name="uq_publications_doi"),
    )
    for field in ("pubmed_id", "doi", "publication_date", "source"):
        op.create_index(f"ix_publications_{field}", "publications", [field])
    for suffix, entity in (("genes", "gene"), ("proteins", "protein"), ("diseases", "disease")):
        table = f"publication_{suffix}"
        op.create_table(
            table,
            sa.Column("id", sa.BigInteger(), primary_key=True),
            sa.Column(
                "publication_id",
                sa.BigInteger(),
                sa.ForeignKey("publications.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                f"{entity}_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{suffix}.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            *provenance(assertion=True),
            sa.CheckConstraint(
                "evidence_kind IN ('structured_metadata', 'curated')", name="evidence_kind"
            ),
            sa.UniqueConstraint(
                "publication_id",
                f"{entity}_id",
                "source",
                "source_identifier",
                name=f"uq_{table}_source",
            ),
        )
        for field in ("publication_id", f"{entity}_id", "source"):
            op.create_index(f"ix_{table}_{field}", table, [field])
    op.execute(
        "CREATE INDEX ix_publications_search_document ON publications USING gin "
        "(to_tsvector('simple', coalesce(title, '') || ' ' || "
        "coalesce(abstract, '') || ' ' || coalesce(journal, '')))"
    )
    op.execute(
        "CREATE INDEX ix_publications_title_trgm ON publications USING gin (title gin_trgm_ops)"
    )


def downgrade() -> None:
    for table in (
        "publication_diseases",
        "publication_proteins",
        "publication_genes",
        "publications",
    ):
        op.drop_table(table)
