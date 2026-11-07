from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.types import BIGINT_PK

if TYPE_CHECKING:
    from app.models.gene import Gene


class GeneAlias(ProvenanceMixin, Base):
    __tablename__ = "gene_aliases"
    __table_args__ = (
        UniqueConstraint("gene_id", "source", "alias", name="uq_gene_aliases_source"),
        CheckConstraint("length(alias) > 0", name="alias_nonempty"),
        Index(
            "ix_gene_aliases_alias_trgm",
            "alias",
            postgresql_using="gin",
            postgresql_ops={"alias": "gin_trgm_ops"},
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = mapped_column(
        ForeignKey("genes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[str] = mapped_column(String(64), nullable=False)
    gene: Mapped["Gene"] = relationship(back_populates="aliases")


class GeneGenomicLocation(ProvenanceMixin, Base):
    __tablename__ = "gene_genomic_locations"
    __table_args__ = (
        UniqueConstraint(
            "gene_id",
            "source",
            "sequence_accession",
            "start_position",
            "end_position",
            "strand",
            name="uq_gene_genomic_locations_source",
        ),
        CheckConstraint("start_position >= 1", name="start_positive"),
        CheckConstraint("end_position >= start_position", name="position_order"),
        CheckConstraint("strand IN ('+', '-')", name="strand_value"),
        CheckConstraint("length(sequence_accession) > 0", name="sequence_nonempty"),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = mapped_column(
        ForeignKey("genes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence_accession: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chromosome: Mapped[str | None] = mapped_column(String(64))
    start_position: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_position: Mapped[int] = mapped_column(BigInteger, nullable=False)
    strand: Mapped[str] = mapped_column(String(1), nullable=False)
    gene: Mapped["Gene"] = relationship(back_populates="genomic_locations")
