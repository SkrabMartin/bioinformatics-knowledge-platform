"""Add namespaced gene identity and explicit source assertions; no legacy backfill."""

import sqlalchemy as sa
from alembic import op

revision = "20261111_0010"
down_revision = "20261107_0009"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "gene_external_identifiers",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "gene_id",
            sa.BigInteger(),
            sa.ForeignKey("genes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("namespace", sa.String(32), nullable=False),
        sa.Column("accession", sa.String(64), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("namespace", "accession", name="uq_gene_external_identifier_identity"),
        sa.UniqueConstraint(
            "gene_id", "namespace", name="uq_gene_external_identifier_gene_namespace"
        ),
        sa.CheckConstraint("namespace IN ('ncbi_gene', 'ensembl_gene')", name="namespace_value"),
        sa.CheckConstraint("length(accession) > 0", name="accession_nonempty"),
    )
    op.create_index(
        "ix_gene_external_identifiers_gene_id", "gene_external_identifiers", ["gene_id"]
    )
    op.create_table(
        "gene_identifier_evidence",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "identifier_id",
            sa.BigInteger(),
            sa.ForeignKey("gene_external_identifiers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("reported_accession", sa.String(80), nullable=False),
        sa.Column("source_record_version", sa.String(32)),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint(
            "identifier_id",
            "source",
            "source_identifier",
            "reported_accession",
            name="uq_gene_identifier_evidence_assertion",
        ),
    )
    for field in ("identifier_id", "source"):
        op.create_index("ix_gene_identifier_evidence_" + field, "gene_identifier_evidence", [field])


def downgrade() -> None:
    op.drop_table("gene_identifier_evidence")
    op.drop_table("gene_external_identifiers")
