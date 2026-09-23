from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.types import BIGINT_PK


class Disease(ProvenanceMixin, Base):
    __tablename__ = "diseases"
    __table_args__ = (
        UniqueConstraint("name", name="uq_diseases_name"),
        UniqueConstraint("mondo_id", name="uq_diseases_mondo_id"),
        UniqueConstraint("disease_ontology_id", name="uq_diseases_disease_ontology_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    mondo_id: Mapped[str | None] = mapped_column(String(64), index=True)
    disease_ontology_id: Mapped[str | None] = mapped_column(String(64), index=True)
