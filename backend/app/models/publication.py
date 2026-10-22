from typing import TYPE_CHECKING, Literal

from sqlalchemy import (
    JSON,
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
from app.models.relationships import RelationshipProvenanceMixin
from app.models.types import BIGINT_PK

if TYPE_CHECKING:
    from app.models.disease import Disease
    from app.models.gene import Gene
    from app.models.protein import Protein


class Publication(ProvenanceMixin, Base):
    __tablename__ = "publications"
    __table_args__ = (
        CheckConstraint("pubmed_id IS NOT NULL OR doi IS NOT NULL", name="identifier_required"),
        UniqueConstraint("pubmed_id", name="uq_publications_pubmed_id"),
        UniqueConstraint("doi", name="uq_publications_doi"),
        Index(
            "ix_publications_search_document",
            text(
                "to_tsvector('simple', coalesce(title, '') || ' ' || "
                "coalesce(abstract, '') || ' ' || coalesce(journal, ''))"
            ),
            postgresql_using="gin",
        ).ddl_if(dialect="postgresql"),
        Index(
            "ix_publications_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    pubmed_id: Mapped[str | None] = mapped_column(String(32), index=True)
    doi: Mapped[str | None] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text)
    journal: Mapped[str | None] = mapped_column(String(512))
    authors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # ISO partial date: YYYY, YYYY-MM, or YYYY-MM-DD. Never fabricate missing components.
    publication_date: Mapped[str | None] = mapped_column(String(10), index=True)
    publication_date_text: Mapped[str | None] = mapped_column(String(255))


class PublicationEvidenceMixin(RelationshipProvenanceMixin):
    evidence_kind: Mapped[Literal["structured_metadata", "curated"]] = mapped_column(
        String(32), nullable=False
    )
    publication_id: Mapped[int] = mapped_column(
        ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False, index=True
    )


class PublicationGene(PublicationEvidenceMixin, Base):
    __tablename__ = "publication_genes"
    __table_args__ = (
        UniqueConstraint(
            "publication_id",
            "gene_id",
            "source",
            "source_identifier",
            name="uq_publication_genes_source",
        ),
        CheckConstraint(
            "evidence_kind IN ('structured_metadata', 'curated')", name="evidence_kind"
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = mapped_column(ForeignKey("genes.id", ondelete="RESTRICT"), index=True)
    publication: Mapped[Publication] = relationship()
    gene: Mapped["Gene"] = relationship()


class PublicationProtein(PublicationEvidenceMixin, Base):
    __tablename__ = "publication_proteins"
    __table_args__ = (
        UniqueConstraint(
            "publication_id",
            "protein_id",
            "source",
            "source_identifier",
            name="uq_publication_proteins_source",
        ),
        CheckConstraint(
            "evidence_kind IN ('structured_metadata', 'curated')", name="evidence_kind"
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    protein_id: Mapped[int] = mapped_column(
        ForeignKey("proteins.id", ondelete="RESTRICT"), index=True
    )
    publication: Mapped[Publication] = relationship()
    protein: Mapped["Protein"] = relationship()


class PublicationDisease(PublicationEvidenceMixin, Base):
    __tablename__ = "publication_diseases"
    __table_args__ = (
        UniqueConstraint(
            "publication_id",
            "disease_id",
            "source",
            "source_identifier",
            name="uq_publication_diseases_source",
        ),
        CheckConstraint(
            "evidence_kind IN ('structured_metadata', 'curated')", name="evidence_kind"
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("diseases.id", ondelete="RESTRICT"), index=True
    )
    publication: Mapped[Publication] = relationship()
    disease: Mapped["Disease"] = relationship()
