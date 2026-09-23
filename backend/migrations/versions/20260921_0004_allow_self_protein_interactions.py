"""Allow sourced self-interactions for proteins.

Revision ID: 20260921_0004
Revises: 20260921_0003
Create Date: 2026-09-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260921_0004"
down_revision: str | None = "20260921_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_protein_interactions_ordered_pair", "protein_interactions", type_="check"
    )
    op.create_check_constraint(
        "ck_protein_interactions_ordered_pair",
        "protein_interactions",
        "protein_a_id <= protein_b_id",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_protein_interactions_ordered_pair", "protein_interactions", type_="check"
    )
    op.create_check_constraint(
        "ck_protein_interactions_ordered_pair",
        "protein_interactions",
        "protein_a_id < protein_b_id",
    )
