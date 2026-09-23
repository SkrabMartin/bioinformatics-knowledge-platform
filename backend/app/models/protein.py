from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.types import BIGINT_PK

if TYPE_CHECKING:
    from app.models.gene import Gene
    from app.models.organism import Organism


class Protein(ProvenanceMixin, Base):
    __tablename__ = "proteins"
    __table_args__ = (
        UniqueConstraint("accession", name="uq_proteins_accession"),
        Index(
            "ix_proteins_search_document",
            text(
                "to_tsvector('simple', coalesce(accession, '') || ' ' || "
                "coalesce(name, '') || ' ' || "
                "coalesce(function, ''))"
            ),
            postgresql_using="gin",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "sequence_length IS NULL OR sequence_length > 0", name="sequence_length_positive"
        ),
        Index(
            "ix_proteins_accession_trgm",
            "accession",
            postgresql_using="gin",
            postgresql_ops={"accession": "gin_trgm_ops"},
        ),
        Index(
            "ix_proteins_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    accession: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    gene_id: Mapped[int | None] = mapped_column(
        ForeignKey("genes.id", ondelete="RESTRICT"), index=True
    )
    organism_id: Mapped[int] = mapped_column(
        ForeignKey("organisms.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    function: Mapped[str | None] = mapped_column(Text)
    sequence_length: Mapped[int | None] = mapped_column(Integer)

    gene: Mapped["Gene | None"] = relationship(back_populates="proteins")
    organism: Mapped["Organism"] = relationship(back_populates="proteins")
