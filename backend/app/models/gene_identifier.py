from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ProvenanceMixin, TimestampMixin
from app.models.types import BIGINT_PK

if TYPE_CHECKING:
    from app.models.gene import Gene


class GeneExternalIdentifier(TimestampMixin, Base):
    __tablename__ = "gene_external_identifiers"
    __table_args__ = (
        UniqueConstraint("namespace", "accession", name="uq_gene_external_identifier_identity"),
        UniqueConstraint("gene_id", "namespace", name="uq_gene_external_identifier_gene_namespace"),
        CheckConstraint("namespace IN ('ncbi_gene', 'ensembl_gene')", name="namespace_value"),
        CheckConstraint("length(accession) > 0", name="accession_nonempty"),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = mapped_column(
        ForeignKey("genes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    namespace: Mapped[str] = mapped_column(String(32), nullable=False)
    accession: Mapped[str] = mapped_column(String(64), nullable=False)
    gene: Mapped["Gene"] = relationship(back_populates="external_identifiers")
    evidence: Mapped[list["GeneIdentifierEvidence"]] = relationship(
        back_populates="identifier", order_by="GeneIdentifierEvidence.id"
    )


class GeneIdentifierEvidence(ProvenanceMixin, Base):
    __tablename__ = "gene_identifier_evidence"
    __table_args__ = (
        UniqueConstraint(
            "identifier_id",
            "source",
            "source_identifier",
            "reported_accession",
            name="uq_gene_identifier_evidence_assertion",
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    identifier_id: Mapped[int] = mapped_column(
        ForeignKey("gene_external_identifiers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    reported_accession: Mapped[str] = mapped_column(String(80), nullable=False)
    source_record_version: Mapped[str | None] = mapped_column(String(32))
    identifier: Mapped[GeneExternalIdentifier] = relationship(back_populates="evidence")
