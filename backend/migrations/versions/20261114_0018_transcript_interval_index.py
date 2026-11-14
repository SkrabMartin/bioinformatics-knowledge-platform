"""Index exact assembly/region transcript span queries without altering records."""

from alembic import op

revision = "20261114_0018"
down_revision = "20261114_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_transcripts_interval",
        "transcripts",
        ["assembly_name", "sequence_region", "start_position", "end_position"],
    )


def downgrade() -> None:
    op.drop_index("ix_transcripts_interval", table_name="transcripts")
