"""Reuse the single-record import boundaries; never manufacture missing records."""

import httpx2
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.publications import PublicationIngestionService
from app.ingestion.services import GeneIngestionService, ProteinIngestionService
from app.integrations.http import RetryingJsonClient
from app.integrations.ncbi import NcbiGeneAdapter
from app.integrations.ncbi.pubmed import PubMedAdapter
from app.integrations.uniprot import UniProtAdapter
from app.models.import_job import ImportJob, ImportJobItem


class ProviderImporter:
    def __init__(self, settings: Settings, client: httpx2.Client) -> None:
        self.settings = settings
        # Queue-level retries own the attempt budget. Shared pacing covers both
        # NCBI adapters and every HTTP request, not just the start of each record.
        self.transport = RetryingJsonClient(
            client,
            provider="Import provider",
            max_attempts=1,
            backoff_seconds=0,
            min_interval_seconds=settings.import_request_interval_seconds,
        )

    def __call__(self, session: Session, job: ImportJob, item: ImportJobItem) -> dict[str, object]:
        settings = self.settings
        api_key = settings.ncbi_api_key.get_secret_value() if settings.ncbi_api_key else None
        if job.entity_type == "gene":
            provider = NcbiGeneAdapter(
                self.transport,
                base_url=settings.ncbi_base_url,
                tool=settings.ncbi_tool,
                email=settings.ncbi_email,
                api_key=api_key,
            )
            return (
                GeneIngestionService(session, provider)
                .import_gene(item.identifier, job.taxonomy_id or "")
                .model_dump()
            )
        if job.entity_type == "publication":
            publication_provider = PubMedAdapter(
                self.transport,
                base_url=settings.ncbi_base_url,
                tool=settings.ncbi_tool,
                email=settings.ncbi_email,
                api_key=api_key,
            )
            return (
                PublicationIngestionService(session, publication_provider)
                .import_publication(item.identifier)
                .model_dump()
            )
        protein_provider = UniProtAdapter(self.transport, base_url=settings.uniprot_base_url)
        return (
            ProteinIngestionService(session, protein_provider)
            .import_protein(item.identifier)
            .model_dump()
        )
