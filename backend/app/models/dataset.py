from datetime import date, datetime
from typing import Literal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.publication import Publication
from app.models.relationships import RelationshipProvenanceMixin
from app.models.types import BIGINT_PK


class Dataset(ProvenanceMixin, Base):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("repository", "accession", name="uq_datasets_repository_accession"),
        CheckConstraint("repository = 'GEO'", name="repository_value"),
        CheckConstraint(
            "sample_count IS NULL OR sample_count BETWEEN 0 AND 100000", name="sample_count_range"
        ),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    repository: Mapped[str] = mapped_column(String(32), nullable=False)
    accession: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    experiment_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    organism_names: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    taxonomy_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    platform_accessions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    publication_pmids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    sample_count: Mapped[int | None] = mapped_column(Integer)
    source_updated_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DatasetPublication(RelationshipProvenanceMixin, Base):
    """First observed GEO citation; retained if later metadata stop listing it."""

    __tablename__ = "dataset_publications"
    __table_args__ = (
        UniqueConstraint("dataset_id", "publication_id", name="uq_dataset_publications_identity"),
        CheckConstraint("evidence_kind = 'structured_metadata'", name="evidence_kind"),
    )
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    publication_id: Mapped[int] = mapped_column(
        ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reported_pmid: Mapped[str] = mapped_column(String(32), nullable=False)
    source_record_date: Mapped[date] = mapped_column(Date, nullable=False)
    evidence_kind: Mapped[Literal["structured_metadata"]] = mapped_column(
        String(32), nullable=False
    )
    dataset: Mapped[Dataset] = relationship()
    publication: Mapped[Publication] = relationship()
