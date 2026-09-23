from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.types import BIGINT_PK

if TYPE_CHECKING:
    from app.models.organism import Organism


class Variant(ProvenanceMixin, Base):
    __tablename__ = "variants"
    __table_args__ = (
        CheckConstraint("rsid IS NOT NULL OR hgvs IS NOT NULL", name="identifier_required"),
        UniqueConstraint("rsid", name="uq_variants_rsid"),
        UniqueConstraint("hgvs", name="uq_variants_hgvs"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    rsid: Mapped[str | None] = mapped_column(String(64), index=True)
    hgvs: Mapped[str | None] = mapped_column(String(512), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    organism_id: Mapped[int] = mapped_column(
        ForeignKey("organisms.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    organism: Mapped["Organism"] = relationship()
