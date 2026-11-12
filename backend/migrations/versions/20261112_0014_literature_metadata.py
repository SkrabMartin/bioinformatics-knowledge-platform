"""Add supplied publication keywords and sourced variant literature links."""

import sqlalchemy as sa
from alembic import op

revision = "20261112_0014"
down_revision = "20261112_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "publications",
        sa.Column("keywords", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.create_table(
        "publication_variants",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "publication_id",
            sa.BigInteger(),
            sa.ForeignKey("publications.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "variant_id",
            sa.BigInteger(),
            sa.ForeignKey("variants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column("evidence_text", sa.Text()),
        sa.Column("evidence_kind", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "publication_id",
            "variant_id",
            "source",
            "source_identifier",
            name="uq_publication_variants_source",
        ),
        sa.CheckConstraint(
            "evidence_kind IN ('structured_metadata', 'curated')", name="evidence_kind"
        ),
    )
    for field in ("publication_id", "variant_id", "source"):
        op.create_index(f"ix_publication_variants_{field}", "publication_variants", [field])


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM publication_variants")) or connection.scalar(
        sa.text("SELECT count(*) FROM publications WHERE CAST(keywords AS TEXT) <> '[]'")
    ):
        raise RuntimeError("Refusing to discard literature metadata; retain additive schema.")
    op.drop_table("publication_variants")
    op.drop_column("publications", "keywords")
