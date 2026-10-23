"""Add pathways, GO aspects and explicit direct annotations / is_a assertions.

Revision ID: 20261023_0006
Revises: 20261022_0005
"""

import sqlalchemy as sa
from alembic import op

revision = "20261023_0006"
down_revision = "20261022_0005"
branch_labels = None
depends_on = None


def provenance(*, assertion: bool = False, annotation: bool = False) -> list[sa.Column]:
    columns = [
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("source_release", sa.String(128), nullable=False),
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
        columns.append(sa.Column("evidence_text", sa.Text()))
    if annotation:
        columns.extend(
            [
                sa.Column("evidence_kind", sa.String(32), nullable=False),
                sa.Column("evidence_code", sa.String(16)),
            ]
        )
    return columns


def indexes(table: str, *fields: str) -> None:
    for field in ("source", *fields):
        op.create_index(f"ix_{table}_{field}", table, [field])


def upgrade() -> None:
    op.create_table(
        "pathways",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "organism_id", sa.BigInteger(), sa.ForeignKey("organisms.id", ondelete="RESTRICT")
        ),
        *provenance(),
        sa.UniqueConstraint("source", "source_identifier", name="uq_pathways_source"),
    )
    indexes("pathways", "name", "organism_id")
    op.create_table(
        "ontology_terms",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("go_id", sa.String(10), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        *provenance(),
        sa.UniqueConstraint("go_id", name="uq_ontology_terms_go_id"),
        sa.UniqueConstraint("id", "kind", name="uq_ontology_terms_id_kind"),
        sa.CheckConstraint("kind IN ('biological_process', 'molecular_function')", name="kind"),
    )
    indexes("ontology_terms", "name", "go_id", "kind")
    op.create_table(
        "gene_pathways",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "gene_id",
            sa.BigInteger(),
            sa.ForeignKey("genes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "pathway_id",
            sa.BigInteger(),
            sa.ForeignKey("pathways.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *provenance(assertion=True, annotation=True),
        sa.UniqueConstraint(
            "gene_id", "pathway_id", "source", "source_identifier", name="uq_gene_pathways_source"
        ),
        sa.CheckConstraint(
            "evidence_kind IN ('curated', 'structured_metadata')", name="evidence_kind"
        ),
    )
    indexes("gene_pathways", "gene_id", "pathway_id")
    for table, entity, kind, unique in (
        ("gene_biological_processes", "gene", "biological_process", "uq_gene_process_source"),
        (
            "protein_molecular_functions",
            "protein",
            "molecular_function",
            "uq_protein_function_source",
        ),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.BigInteger(), primary_key=True),
            sa.Column(
                f"{entity}_id",
                sa.BigInteger(),
                sa.ForeignKey(f"{entity}s.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("term_id", sa.BigInteger(), nullable=False),
            sa.Column("kind", sa.String(32), nullable=False),
            *provenance(assertion=True, annotation=True),
            sa.ForeignKeyConstraint(
                ["term_id", "kind"],
                ["ontology_terms.id", "ontology_terms.kind"],
                ondelete="RESTRICT",
            ),
            sa.CheckConstraint(f"kind = '{kind}'", name="kind"),
            sa.CheckConstraint(
                "evidence_kind IN ('curated', 'structured_metadata')", name="evidence_kind"
            ),
            sa.UniqueConstraint(
                f"{entity}_id", "term_id", "source", "source_identifier", name=unique
            ),
        )
        indexes(table, f"{entity}_id", "term_id")
    op.create_table(
        "ontology_parents",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("child_id", sa.BigInteger(), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        *provenance(assertion=True),
        sa.ForeignKeyConstraint(
            ["child_id", "kind"], ["ontology_terms.id", "ontology_terms.kind"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["parent_id", "kind"], ["ontology_terms.id", "ontology_terms.kind"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("child_id <> parent_id", name="not_self"),
        sa.CheckConstraint("kind IN ('biological_process', 'molecular_function')", name="kind"),
        sa.UniqueConstraint(
            "child_id", "parent_id", "source", "source_identifier", name="uq_ontology_parent_source"
        ),
    )
    indexes("ontology_parents", "child_id", "parent_id")


def downgrade() -> None:
    for table in (
        "ontology_parents",
        "protein_molecular_functions",
        "gene_biological_processes",
        "gene_pathways",
        "ontology_terms",
        "pathways",
    ):
        op.drop_table(table)
