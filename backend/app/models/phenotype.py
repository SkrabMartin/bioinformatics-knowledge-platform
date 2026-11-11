from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.disease import Disease
from app.models.types import BIGINT_PK


class Phenotype(ProvenanceMixin, Base):
    __tablename__ = "phenotypes"
    __table_args__ = (
        UniqueConstraint("hpo_id", name="uq_phenotypes_hpo_id"),
        CheckConstraint("length(hpo_id) = 10 AND hpo_id LIKE 'HP:_______'", name="hpo_shape"),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    hpo_id: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    source_release: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DiseasePhenotype(ProvenanceMixin, Base):
    __tablename__ = "disease_phenotypes"
    __table_args__ = (
        UniqueConstraint(
            "disease_id",
            "phenotype_id",
            "source",
            "source_identifier",
            "source_release",
            "qualifier",
            name="uq_disease_phenotypes_assertion",
        ),
        CheckConstraint("qualifier IN ('present', 'excluded')", name="qualifier_value"),
        CheckConstraint(
            "evidence_kind IN ('curated', 'structured_metadata')", name="evidence_kind_value"
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("diseases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    phenotype_id: Mapped[int] = mapped_column(
        ForeignKey("phenotypes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    qualifier: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_code: Mapped[str | None] = mapped_column(String(32))
    reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    source_release: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    disease: Mapped[Disease] = relationship()
    phenotype: Mapped[Phenotype] = relationship()
