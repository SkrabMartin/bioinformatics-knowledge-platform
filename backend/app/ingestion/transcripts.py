import re
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.errors import IngestionPersistenceError
from app.ingestion.transcript_models import ENSEMBL_GENE_PATTERN, NormalizedTranscriptBatch
from app.models import Gene, GeneExternalIdentifier, Organism
from app.models.transcript import Transcript


class TranscriptProvider(Protocol):
    def fetch_transcripts(self, ensembl_gene_id: str) -> NormalizedTranscriptBatch: ...


class TranscriptImportResult(BaseModel):
    gene_id: int
    ensembl_gene_id: str
    created: int
    updated: int
    unchanged: int


class TranscriptIngestionService:
    def __init__(self, session: Session, provider: TranscriptProvider) -> None:
        self.session, self.provider = session, provider

    def import_transcripts(self, ensembl_gene_id: str) -> TranscriptImportResult:
        if not re.fullmatch(ENSEMBL_GENE_PATTERN, ensembl_gene_id):
            raise ValueError("A versionless Ensembl gene identifier is required.")
        gene_id = self.session.scalar(
            select(Gene.id).where(Gene.ensembl_gene_id == ensembl_gene_id)
        )
        if gene_id is None:
            raise IngestionPersistenceError(
                "Import requires an existing gene with this Ensembl ID."
            )
        # No database lock is held over external requests.
        self.session.rollback()
        batch = self.provider.fetch_transcripts(ensembl_gene_id)
        counts = {"created": 0, "updated": 0, "unchanged": 0}
        try:
            gene = self.session.scalar(
                select(Gene)
                .where(Gene.id == gene_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                gene is None
                or gene.ensembl_gene_id != batch.ensembl_gene_id
                or batch.ensembl_gene_id != ensembl_gene_id
            ):
                raise IngestionPersistenceError(
                    "Gene identity changed or the provider returned another gene."
                )
            registered = self.session.scalar(
                select(GeneExternalIdentifier).where(
                    GeneExternalIdentifier.namespace == "ensembl_gene",
                    GeneExternalIdentifier.accession == ensembl_gene_id,
                )
            )
            if registered is not None and registered.gene_id != gene.id:
                raise IngestionPersistenceError(
                    "Registered Ensembl identity conflicts with the gene."
                )
            taxonomy = self.session.scalar(
                select(Organism.taxonomy_id).where(Organism.id == gene.organism_id)
            )
            if taxonomy != batch.taxonomy_id:
                raise IngestionPersistenceError("Transcript and local gene taxonomy do not agree.")
            for record in batch.transcripts:
                transcript = self.session.scalar(
                    select(Transcript)
                    .where(Transcript.ensembl_transcript_id == record.ensembl_transcript_id)
                    .with_for_update()
                )
                values = record.model_dump()
                values.update(
                    source="Ensembl",
                    source_identifier=record.ensembl_transcript_id,
                    source_release=batch.source_release,
                    source_url=f"https://www.ensembl.org/id/{record.ensembl_transcript_id}",
                )
                if transcript is None:
                    transcript = Transcript(gene_id=gene.id, **values)
                    self.session.add(transcript)
                    counts["created"] += 1
                else:
                    if transcript.gene_id != gene.id:
                        raise IngestionPersistenceError(
                            "Transcript is already linked to another gene."
                        )
                    if int(transcript.source_release) > int(batch.source_release) or (
                        transcript.version is not None
                        and (record.version is None or record.version < transcript.version)
                    ):
                        raise IngestionPersistenceError(
                            "Transcript version/release regression was rejected."
                        )
                    changed = any(
                        getattr(transcript, key) != value for key, value in values.items()
                    )
                    counts["updated" if changed else "unchanged"] += 1
                    for key, value in values.items():
                        setattr(transcript, key, value)
                transcript.imported_at = batch.retrieved_at
            self.session.flush()
            total = (
                self.session.scalar(
                    select(func.count())
                    .select_from(Transcript)
                    .where(Transcript.gene_id == gene.id)
                )
                or 0
            )
            if total > 500:
                raise IngestionPersistenceError("Retained transcript limit exceeded.")
            self.session.commit()
        except (IngestionPersistenceError, IntegrityError) as exc:
            self.session.rollback()
            if isinstance(exc, IngestionPersistenceError):
                raise
            raise IngestionPersistenceError(
                "Transcript import conflicts with stored identity."
            ) from exc
        return TranscriptImportResult(gene_id=gene_id, ensembl_gene_id=ensembl_gene_id, **counts)
