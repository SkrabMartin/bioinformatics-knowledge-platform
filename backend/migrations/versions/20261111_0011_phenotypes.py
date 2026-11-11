"""Add sourced phenotypes and explicitly qualified disease annotations."""

import sqlalchemy as sa
from alembic import op

revision = "20261111_0011"
down_revision = "20261111_0010"
branch_labels = None
depends_on = None


def provenance() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "phenotypes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("hpo_id", sa.String(10), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("description", sa.Text()),
        *provenance(),
        sa.UniqueConstraint("hpo_id", name="uq_phenotypes_hpo_id"),
        sa.CheckConstraint("length(hpo_id) = 10 AND hpo_id LIKE 'HP:_______'", name="hpo_shape"),
    )
    op.create_index("ix_phenotypes_name", "phenotypes", ["name"])
    op.create_index("ix_phenotypes_source", "phenotypes", ["source"])
    op.create_table(
        "disease_phenotypes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "disease_id",
            sa.BigInteger(),
            sa.ForeignKey("diseases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "phenotype_id",
            sa.BigInteger(),
            sa.ForeignKey("phenotypes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("qualifier", sa.String(16), nullable=False),
        sa.Column("evidence_kind", sa.String(32), nullable=False),
        sa.Column("evidence_code", sa.String(32)),
        sa.Column("reference", sa.String(255), nullable=False),
        *provenance(),
        sa.UniqueConstraint(
            "disease_id",
            "phenotype_id",
            "source",
            "source_identifier",
            "source_release",
            "qualifier",
            name="uq_disease_phenotypes_assertion",
        ),
        sa.CheckConstraint("qualifier IN ('present', 'excluded')", name="qualifier_value"),
        sa.CheckConstraint(
            "evidence_kind IN ('curated', 'structured_metadata')", name="evidence_kind_value"
        ),
    )
    for field in ["disease_id", "phenotype_id", "source"]:
        op.create_index("ix_disease_phenotypes_" + field, "disease_phenotypes", [field])


def downgrade() -> None:
    op.drop_table("disease_phenotypes")
    op.drop_table("phenotypes")
