from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.types import BIGINT_PK

if TYPE_CHECKING:
    from app.models.disease import Disease
    from app.models.gene import Gene
    from app.models.protein import Protein
    from app.models.variant import Variant


class RelationshipProvenanceMixin(ProvenanceMixin):
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_text: Mapped[str | None] = mapped_column(Text)


class GeneDiseaseAssociation(RelationshipProvenanceMixin, Base):
    __tablename__ = "gene_disease_associations"
    __table_args__ = (
        UniqueConstraint(
            "gene_id", "disease_id", "source", "source_identifier", name="uq_gene_disease_source"
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = mapped_column(
        ForeignKey("genes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("diseases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    gene: Mapped["Gene"] = relationship()
    disease: Mapped["Disease"] = relationship()


class VariantGeneLocation(RelationshipProvenanceMixin, Base):
    __tablename__ = "variant_gene_locations"
    __table_args__ = (
        UniqueConstraint(
            "variant_id", "gene_id", "source", "source_identifier", name="uq_variant_gene_source"
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("variants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    gene_id: Mapped[int] = mapped_column(
        ForeignKey("genes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    variant: Mapped["Variant"] = relationship()
    gene: Mapped["Gene"] = relationship()


class VariantDiseaseAssociation(RelationshipProvenanceMixin, Base):
    __tablename__ = "variant_disease_associations"
    __table_args__ = (
        UniqueConstraint(
            "variant_id",
            "disease_id",
            "source",
            "source_identifier",
            name="uq_variant_disease_source",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("variants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("diseases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    variant: Mapped["Variant"] = relationship()
    disease: Mapped["Disease"] = relationship()


class ProteinInteraction(RelationshipProvenanceMixin, Base):
    __tablename__ = "protein_interactions"
    __table_args__ = (
        CheckConstraint("protein_a_id <= protein_b_id", name="ordered_pair"),
        UniqueConstraint(
            "protein_a_id",
            "protein_b_id",
            "source",
            "source_identifier",
            name="uq_protein_interaction_source",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    protein_a_id: Mapped[int] = mapped_column(
        ForeignKey("proteins.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    protein_b_id: Mapped[int] = mapped_column(
        ForeignKey("proteins.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    protein_a: Mapped["Protein"] = relationship(foreign_keys=[protein_a_id])
    protein_b: Mapped["Protein"] = relationship(foreign_keys=[protein_b_id])
