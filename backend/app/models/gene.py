from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
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
    from app.models.organism import Organism
    from app.models.protein import Protein


class Gene(ProvenanceMixin, Base):
    __tablename__ = "genes"
    __table_args__ = (
        UniqueConstraint("organism_id", "symbol", name="uq_genes_organism_symbol"),
        UniqueConstraint("ncbi_gene_id", name="uq_genes_ncbi_gene_id"),
        UniqueConstraint("ensembl_gene_id", name="uq_genes_ensembl_gene_id"),
        Index(
            "ix_genes_search_document",
            text(
                "to_tsvector('simple', coalesce(symbol, '') || ' ' || coalesce(name, '') || ' ' || "
                "coalesce(description, '') || ' ' || coalesce(ncbi_gene_id, '') || ' ' || "
                "coalesce(ensembl_gene_id, ''))"
            ),
            postgresql_using="gin",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint("start_position IS NULL OR start_position >= 0", name="start_nonnegative"),
        CheckConstraint("end_position IS NULL OR end_position >= 0", name="end_nonnegative"),
        CheckConstraint(
            "start_position IS NULL OR end_position IS NULL OR end_position >= start_position",
            name="position_order",
        ),
        CheckConstraint("strand IS NULL OR strand IN ('+', '-')", name="strand_value"),
        Index("ix_genes_organism_symbol", "organism_id", "symbol"),
        Index(
            "ix_genes_symbol_trgm",
            "symbol",
            postgresql_using="gin",
            postgresql_ops={"symbol": "gin_trgm_ops"},
        ),
        Index(
            "ix_genes_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_genes_ncbi_gene_id_trgm",
            "ncbi_gene_id",
            postgresql_using="gin",
            postgresql_ops={"ncbi_gene_id": "gin_trgm_ops"},
        ),
        Index(
            "ix_genes_ensembl_gene_id_trgm",
            "ensembl_gene_id",
            postgresql_using="gin",
            postgresql_ops={"ensembl_gene_id": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    organism_id: Mapped[int] = mapped_column(
        ForeignKey("organisms.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    chromosome: Mapped[str | None] = mapped_column(String(64))
    start_position: Mapped[int | None] = mapped_column(BigInteger)
    end_position: Mapped[int | None] = mapped_column(BigInteger)
    strand: Mapped[str | None] = mapped_column(String(1))
    ncbi_gene_id: Mapped[str | None] = mapped_column(String(64), index=True)
    ensembl_gene_id: Mapped[str | None] = mapped_column(String(64), index=True)

    organism: Mapped["Organism"] = relationship(back_populates="genes")
    proteins: Mapped[list["Protein"]] = relationship(back_populates="gene")
