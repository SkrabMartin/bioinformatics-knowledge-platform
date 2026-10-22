from typing import Literal, Protocol

from pydantic import ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.services import IngestionPersistenceError
from app.models import Gene, Publication, PublicationGene
from app.schemas.publication import PublicationFields, PublicationImportResult


class NormalizedPublication(PublicationFields):
    model_config = ConfigDict(extra="forbid")
    linked_ncbi_gene_ids: list[str] = Field(default_factory=list, max_length=10000)


class PublicationProvider(Protocol):
    def fetch_publication(self, pubmed_id: str) -> NormalizedPublication: ...


class PublicationIngestionService:
    def __init__(self, session: Session, provider: PublicationProvider) -> None:
        self.session = session
        self.provider = provider

    def import_publication(self, pubmed_id: str) -> PublicationImportResult:
        record = self.provider.fetch_publication(pubmed_id)
        try:
            by_pmid = self.session.scalar(
                select(Publication).where(Publication.pubmed_id == record.pubmed_id)
            )
            by_doi = (
                self.session.scalar(select(Publication).where(Publication.doi == record.doi))
                if record.doi
                else None
            )
            if by_pmid and by_doi and by_pmid.id != by_doi.id:
                raise IngestionPersistenceError(
                    "PMID and DOI identify different publication records."
                )
            publication = by_pmid or by_doi
            values = record.model_dump(exclude={"linked_ncbi_gene_ids"})
            values["source_url"] = str(record.source_url) if record.source_url else None
            changed = False
            if publication is None:
                publication = Publication(**values)
                self.session.add(publication)
                action: Literal["created", "updated", "unchanged"] = "created"
            else:
                if publication.pubmed_id not in (None, record.pubmed_id):
                    raise IngestionPersistenceError("DOI is already assigned to another PMID.")
                if publication.doi and record.doi and publication.doi != record.doi:
                    raise IngestionPersistenceError("PMID is already assigned to another DOI.")
                # A temporarily absent DOI must not erase a previously established identity.
                if record.doi is None:
                    values.pop("doi")
                changed = any(
                    getattr(publication, key) != value
                    for key, value in values.items()
                    if key != "imported_at"
                )
                for key, value in values.items():
                    setattr(publication, key, value)
                action = "updated" if changed else "unchanged"
            self.session.flush()
            links_created = 0
            genes = self.session.scalars(
                select(Gene).where(Gene.ncbi_gene_id.in_(record.linked_ncbi_gene_ids))
            ).all()
            for gene in genes:
                source_id = f"{record.pubmed_id}:gene:{gene.ncbi_gene_id}"
                existing = self.session.scalar(
                    select(PublicationGene).where(
                        PublicationGene.publication_id == publication.id,
                        PublicationGene.gene_id == gene.id,
                        PublicationGene.source == "NCBI PubMed ELink",
                        PublicationGene.source_identifier == source_id,
                    )
                )
                if existing is None:
                    self.session.add(
                        PublicationGene(
                            publication_id=publication.id,
                            gene_id=gene.id,
                            source="NCBI PubMed ELink",
                            source_identifier=source_id,
                            source_url=values["source_url"],
                            imported_at=record.imported_at,
                            evidence_kind="structured_metadata",
                            evidence_text=(
                                "NCBI pubmed_gene structured link; "
                                "not a causal or clinical assertion."
                            ),
                        )
                    )
                    links_created += 1
                else:
                    existing.imported_at = record.imported_at
            self.session.commit()
        except (IntegrityError, IngestionPersistenceError) as exc:
            self.session.rollback()
            if isinstance(exc, IngestionPersistenceError):
                raise
            raise IngestionPersistenceError(
                "Publication import conflicts with an existing identifier or assertion."
            ) from exc
        return PublicationImportResult(
            entity_id=publication.id,
            identifier=record.pubmed_id or record.doi or "",
            action=action,
            gene_links_created=links_created,
        )
