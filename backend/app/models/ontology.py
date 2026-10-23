from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.relationships import RelationshipProvenanceMixin
from app.models.types import BIGINT_PK

if TYPE_CHECKING:
    from app.models.gene import Gene
    from app.models.protein import Protein


class KnowledgeRecordMixin(ProvenanceMixin):
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    source_release: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)


class Pathway(KnowledgeRecordMixin, Base):
    __tablename__ = "pathways"
    __table_args__ = (UniqueConstraint("source", "source_identifier", name="uq_pathways_source"),)
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    organism_id: Mapped[int | None] = mapped_column(
        ForeignKey("organisms.id", ondelete="RESTRICT"), index=True
    )


class OntologyTerm(KnowledgeRecordMixin, Base):
    __tablename__ = "ontology_terms"
    __table_args__ = (
        UniqueConstraint("go_id", name="uq_ontology_terms_go_id"),
        UniqueConstraint("id", "kind", name="uq_ontology_terms_id_kind"),
        CheckConstraint("kind IN ('biological_process', 'molecular_function')", name="kind"),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    go_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    __mapper_args__ = {  # noqa: RUF012 -- SQLAlchemy's mapper configuration attribute.
        "polymorphic_on": kind,
        "polymorphic_abstract": True,
    }


class BiologicalProcess(OntologyTerm):
    __mapper_args__ = {"polymorphic_identity": "biological_process"}  # noqa: RUF012


class MolecularFunction(OntologyTerm):
    __mapper_args__ = {"polymorphic_identity": "molecular_function"}  # noqa: RUF012


class AnnotationMixin(RelationshipProvenanceMixin):
    source_release: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_code: Mapped[str | None] = mapped_column(String(16))
    evidence_kind: Mapped[str] = mapped_column(String(32), nullable=False)


class GenePathway(AnnotationMixin, Base):
    __tablename__ = "gene_pathways"
    __table_args__ = (
        UniqueConstraint(
            "gene_id", "pathway_id", "source", "source_identifier", name="uq_gene_pathways_source"
        ),
        CheckConstraint(
            "evidence_kind IN ('curated', 'structured_metadata')", name="evidence_kind"
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = mapped_column(ForeignKey("genes.id", ondelete="RESTRICT"), index=True)
    pathway_id: Mapped[int] = mapped_column(
        ForeignKey("pathways.id", ondelete="RESTRICT"), index=True
    )
    gene: Mapped["Gene"] = relationship()
    pathway: Mapped[Pathway] = relationship()


class GeneBiologicalProcess(AnnotationMixin, Base):
    __tablename__ = "gene_biological_processes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["term_id", "kind"], ["ontology_terms.id", "ontology_terms.kind"], ondelete="RESTRICT"
        ),
        CheckConstraint("kind = 'biological_process'", name="kind"),
        CheckConstraint(
            "evidence_kind IN ('curated', 'structured_metadata')", name="evidence_kind"
        ),
        UniqueConstraint(
            "gene_id", "term_id", "source", "source_identifier", name="uq_gene_process_source"
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = mapped_column(ForeignKey("genes.id", ondelete="RESTRICT"), index=True)
    term_id: Mapped[int] = mapped_column(BIGINT_PK, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="biological_process")
    gene: Mapped["Gene"] = relationship()
    term: Mapped[OntologyTerm] = relationship(viewonly=True)


class ProteinMolecularFunction(AnnotationMixin, Base):
    __tablename__ = "protein_molecular_functions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["term_id", "kind"], ["ontology_terms.id", "ontology_terms.kind"], ondelete="RESTRICT"
        ),
        CheckConstraint("kind = 'molecular_function'", name="kind"),
        CheckConstraint(
            "evidence_kind IN ('curated', 'structured_metadata')", name="evidence_kind"
        ),
        UniqueConstraint(
            "protein_id",
            "term_id",
            "source",
            "source_identifier",
            name="uq_protein_function_source",
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    protein_id: Mapped[int] = mapped_column(
        ForeignKey("proteins.id", ondelete="RESTRICT"), index=True
    )
    term_id: Mapped[int] = mapped_column(BIGINT_PK, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="molecular_function")
    protein: Mapped["Protein"] = relationship()
    term: Mapped[OntologyTerm] = relationship(viewonly=True)


class OntologyParent(RelationshipProvenanceMixin, Base):
    __tablename__ = "ontology_parents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["child_id", "kind"], ["ontology_terms.id", "ontology_terms.kind"], ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["parent_id", "kind"], ["ontology_terms.id", "ontology_terms.kind"], ondelete="RESTRICT"
        ),
        CheckConstraint("child_id <> parent_id", name="not_self"),
        CheckConstraint("kind IN ('biological_process', 'molecular_function')", name="kind"),
        UniqueConstraint(
            "child_id", "parent_id", "source", "source_identifier", name="uq_ontology_parent_source"
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(BIGINT_PK, index=True)
    parent_id: Mapped[int] = mapped_column(BIGINT_PK, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_release: Mapped[str] = mapped_column(String(128), nullable=False)
    child: Mapped[OntologyTerm] = relationship(foreign_keys=[child_id, kind], viewonly=True)
    parent: Mapped[OntologyTerm] = relationship(foreign_keys=[parent_id, kind], viewonly=True)
