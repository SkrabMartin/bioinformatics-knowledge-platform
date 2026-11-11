from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.types import BIGINT_PK


class VariantPlacement(ProvenanceMixin, Base):
    __tablename__ = "variant_placements"
    __table_args__ = (
        UniqueConstraint(
            "variant_id",
            "representation_key",
            "source",
            "source_identifier",
            "source_release",
            name="uq_variant_placement_assertion",
        ),
        CheckConstraint(
            "start_position >= 1 AND end_position >= start_position", name="coordinate_order"
        ),
        CheckConstraint("coordinate_system = 'one_based_closed'", name="coordinate_system_value"),
        CheckConstraint("strand = '+'", name="strand_value"),
        CheckConstraint(
            "length(reference_allele) BETWEEN 1 AND 1000 "
            "AND length(alternate_allele) BETWEEN 1 AND 1000",
            name="allele_length",
        ),
        CheckConstraint(
            "end_position - start_position + 1 = length(reference_allele)", name="reference_span"
        ),
        CheckConstraint("reference_allele <> alternate_allele", name="alleles_differ"),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("variants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    representation_key: Mapped[str] = mapped_column(String(64), nullable=False)
    assembly_name: Mapped[str] = mapped_column(String(128), nullable=False)
    assembly_accession: Mapped[str | None] = mapped_column(String(32))
    sequence_accession: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence_region: Mapped[str | None] = mapped_column(String(128))
    taxonomy_id: Mapped[str] = mapped_column(String(16), nullable=False)
    coordinate_system: Mapped[str] = mapped_column(String(32), nullable=False)
    strand: Mapped[str] = mapped_column(String(1), nullable=False)
    start_position: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_position: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reference_allele: Mapped[str] = mapped_column(String(1000), nullable=False)
    alternate_allele: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    source_release: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
