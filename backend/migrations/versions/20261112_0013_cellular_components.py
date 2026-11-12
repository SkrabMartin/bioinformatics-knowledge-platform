"""Extend GO aspects with cellular components and direct sourced protein annotations."""

import sqlalchemy as sa
from alembic import op

revision = "20261112_0013"
down_revision = "20261111_0012"
branch_labels = None
depends_on = None

OLD_KINDS = "kind IN ('biological_process', 'molecular_function')"
ALL_KINDS = "kind IN ('biological_process', 'molecular_function', 'cellular_component')"


def change_kinds(expression: str) -> None:
    for table in ("ontology_terms", "ontology_parents"):
        name = op.f(f"ck_{table}_kind")
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, expression)


def upgrade() -> None:
    change_kinds(ALL_KINDS)
    op.create_table(
        "protein_cellular_components",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "protein_id",
            sa.BigInteger(),
            sa.ForeignKey("proteins.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("term_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column("evidence_text", sa.Text()),
        sa.Column("source_release", sa.String(128), nullable=False),
        sa.Column("evidence_code", sa.String(16)),
        sa.Column("evidence_kind", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["term_id", "kind"], ["ontology_terms.id", "ontology_terms.kind"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("kind = 'cellular_component'", name="kind"),
        sa.CheckConstraint(
            "evidence_kind IN ('curated', 'structured_metadata')", name="evidence_kind"
        ),
        sa.UniqueConstraint(
            "protein_id",
            "term_id",
            "source",
            "source_identifier",
            name="uq_protein_component_source",
        ),
    )
    for field in ("protein_id", "term_id", "source"):
        op.create_index(
            f"ix_protein_cellular_components_{field}", "protein_cellular_components", [field]
        )


def downgrade() -> None:
    connection = op.get_bind()
    count = connection.scalar(
        sa.text("SELECT count(*) FROM ontology_terms WHERE kind='cellular_component'")
    )
    annotations = connection.scalar(sa.text("SELECT count(*) FROM protein_cellular_components"))
    if count or annotations:
        raise RuntimeError(
            "Refusing downgrade while cellular component data exist; retain additive schema."
        )
    op.drop_table("protein_cellular_components")
    change_kinds(OLD_KINDS)
