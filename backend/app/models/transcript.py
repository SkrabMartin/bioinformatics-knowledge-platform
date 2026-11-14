from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.types import BIGINT_PK

if TYPE_CHECKING:
    from app.models.gene import Gene


class Transcript(ProvenanceMixin, Base):
    __tablename__ = "transcripts"
    __table_args__ = (
        Index(
            "ix_transcripts_interval",
            "assembly_name",
            "sequence_region",
            "start_position",
            "end_position",
        ),
        UniqueConstraint("ensembl_transcript_id", name="uq_transcripts_ensembl_id"),
        CheckConstraint("start_position >= 1", name="start_positive"),
        CheckConstraint("end_position >= start_position", name="position_order"),
        CheckConstraint("strand IN ('+', '-')", name="strand_value"),
        CheckConstraint("version IS NULL OR version >= 1", name="version_positive"),
        CheckConstraint("source = 'Ensembl'", name="source_value"),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = mapped_column(
        ForeignKey("genes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    ensembl_transcript_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(255))
    biotype: Mapped[str | None] = mapped_column(String(128))
    assembly_name: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence_region: Mapped[str] = mapped_column(String(128), nullable=False)
    start_position: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_position: Mapped[int] = mapped_column(BigInteger, nullable=False)
    strand: Mapped[str] = mapped_column(String(1), nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    source_release: Mapped[str] = mapped_column(String(16), nullable=False)
    gene: Mapped["Gene"] = relationship(back_populates="transcripts")
