import argparse
import json
import logging
import signal
import sys
from pathlib import Path

import httpx2
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import get_engine, get_session_factory
from app.core.logging import configure_logging
from app.fixtures import load_development_fixtures
from app.ingestion.job_provider import ProviderImporter
from app.ingestion.publications import PublicationIngestionService
from app.ingestion.services import (
    GeneIngestionService,
    IngestionPersistenceError,
    ProteinIngestionService,
)
from app.ingestion.transcripts import TranscriptIngestionService
from app.ingestion.worker import run_worker
from app.integrations.ensembl import EnsemblTranscriptAdapter
from app.integrations.errors import IntegrationError
from app.integrations.geo import GeoSeriesAdapter
from app.integrations.http import RetryingJsonClient
from app.integrations.ncbi import NcbiGeneAdapter
from app.integrations.ncbi.pubmed import PubMedAdapter
from app.integrations.uniprot import UniProtAdapter
from app.schemas.import_job import ImportJobCreate
from app.services.datasets import DatasetService
from app.services.errors import ApplicationError
from app.services.import_jobs import ImportJobService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bioinformatics Knowledge Platform utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    fixture_parser = subparsers.add_parser(
        "load-fixtures", help="Load explicitly marked Phase 1 development demo data"
    )
    fixture_parser.add_argument("--path", type=Path, help="Override fixture JSON path")
    dataset_parser = subparsers.add_parser(
        "import-dataset", help="Import metadata for one public GEO Series; no data files"
    )
    dataset_parser.add_argument("accession")
    resolve_parser = subparsers.add_parser(
        "resolve-dataset-publications",
        help="Resolve reported GEO PMIDs to already stored citations",
    )
    resolve_parser.add_argument("accession")
    gene_parser = subparsers.add_parser(
        "import-gene", help="Import or refresh one gene from NCBI Gene"
    )
    gene_parser.add_argument("symbol", help="Exact NCBI Gene symbol, for example TP53")
    gene_parser.add_argument(
        "--taxonomy-id", default="9606", help="NCBI taxonomy ID (default: 9606)"
    )
    protein_parser = subparsers.add_parser(
        "import-protein", help="Import or refresh one protein from UniProtKB"
    )
    protein_parser.add_argument("accession", help="UniProtKB accession, for example P04637")
    publication_parser = subparsers.add_parser(
        "import-publication",
        help="Import one PubMed citation and explicit links to already stored genes",
    )
    publication_parser.add_argument("pubmed_id", help="Numeric PubMed ID")
    transcript_parser = subparsers.add_parser(
        "import-transcripts", help="Import Ensembl transcripts for an existing mapped gene"
    )
    transcript_parser.add_argument("ensembl_gene_id")
    batch_parser = subparsers.add_parser("enqueue-import", help="Queue 1-100 explicit identifiers")
    batch_parser.add_argument("entity_type", choices=["gene", "protein", "publication", "dataset"])
    batch_parser.add_argument("identifiers", nargs="+")
    batch_parser.add_argument("--taxonomy-id")
    batch_parser.add_argument("--max-attempts", type=int, default=3)
    batch_parser.add_argument("--idempotency-key")
    for command in ("import-job", "cancel-import-job"):
        job_parser = subparsers.add_parser(command)
        job_parser.add_argument("job_id")
    worker_parser = subparsers.add_parser("import-worker", help="Run the PostgreSQL import worker")
    worker_parser.add_argument("--once", action="store_true", help="Process at most one ready item")
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    settings = get_settings()
    if arguments.command in {"enqueue-import", "import-job", "cancel-import-job"}:
        try:
            with get_session_factory()() as session:
                service = ImportJobService(session)
                if arguments.command == "enqueue-import":
                    job = service.create(
                        ImportJobCreate(
                            entity_type=arguments.entity_type,
                            identifiers=arguments.identifiers,
                            taxonomy_id=arguments.taxonomy_id,
                            max_attempts=arguments.max_attempts,
                            idempotency_key=arguments.idempotency_key,
                        )
                    )
                elif arguments.command == "cancel-import-job":
                    job = service.cancel(arguments.job_id)
                else:
                    job = service.read(arguments.job_id)
                print(job.model_dump_json())
                if arguments.command == "import-job":
                    print(service.items(job.id, 1, 100).model_dump_json())
        except (ApplicationError, ValueError):
            print('{"error":{"code":"invalid_job_request"}}', file=sys.stderr)
            raise SystemExit(1) from None
        return
    if arguments.command == "resolve-dataset-publications":
        try:
            with get_session_factory()() as session:
                dataset_service = DatasetService(session)
                record = dataset_service.by_accession(arguments.accession)
                resolved_citations = dataset_service.resolve_publications(record.id)
                print(resolved_citations.model_dump_json())
        except (ApplicationError, SQLAlchemyError, ValueError):
            print('{"error":{"code":"dataset_resolution_failed"}}', file=sys.stderr)
            raise SystemExit(1) from None
        return
    if arguments.command == "import-worker":
        configure_logging(settings.log_level, settings.log_json)
        # Avoid client access logs containing provider query credentials.
        logging.getLogger("httpx2").setLevel(logging.WARNING)
        logging.getLogger("httpcore2").setLevel(logging.WARNING)
        stop = False

        def request_stop(_signum: int, _frame: object) -> None:
            nonlocal stop
            stop = True

        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)
        try:
            with httpx2.Client(
                timeout=settings.external_api_timeout_seconds,
                follow_redirects=True,
                headers={
                    "User-Agent": settings.external_api_user_agent,
                    "Accept": "application/json",
                },
            ) as client:
                acquired = run_worker(
                    get_engine(),
                    ProviderImporter(settings, client),
                    once=arguments.once,
                    stopping=lambda: stop,
                    poll_seconds=settings.import_poll_seconds,
                    retry_seconds=settings.import_retry_seconds,
                )
            if not acquired:
                print('{"error":{"code":"import_worker_already_running"}}', file=sys.stderr)
                raise SystemExit(1)
        except Exception:
            # Database exceptions may include connection details; fail without traceback.
            print('{"error":{"code":"import_worker_stopped"}}', file=sys.stderr)
            raise SystemExit(1) from None
        return
    if arguments.command == "load-fixtures":
        path = arguments.path or settings.fixture_path
        with get_session_factory()() as session:
            counts = load_development_fixtures(session, path)
        print(json.dumps(counts, sort_keys=True))
        return

    try:
        with httpx2.Client(
            timeout=settings.external_api_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": settings.external_api_user_agent, "Accept": "application/json"},
        ) as client:
            if arguments.command == "import-dataset":
                transport = RetryingJsonClient(
                    client,
                    provider="NCBI GEO",
                    max_attempts=settings.external_api_max_attempts,
                    backoff_seconds=settings.external_api_backoff_seconds,
                )
                payload = GeoSeriesAdapter(transport).fetch_dataset(arguments.accession)
                with get_session_factory()() as session:
                    record, action = DatasetService(session).save(payload, refresh=True)
                    print(
                        json.dumps(
                            {
                                "entity_type": "dataset",
                                "entity_id": record.id,
                                "identifier": record.accession,
                                "action": action,
                            }
                        )
                    )
                return
            if arguments.command == "import-transcripts":
                transport = RetryingJsonClient(
                    client,
                    provider="Ensembl",
                    max_attempts=settings.external_api_max_attempts,
                    backoff_seconds=settings.external_api_backoff_seconds,
                    min_interval_seconds=settings.import_request_interval_seconds,
                )
                with get_session_factory()() as session:
                    transcript_result = TranscriptIngestionService(
                        session,
                        EnsemblTranscriptAdapter(transport, base_url=settings.ensembl_base_url),
                    ).import_transcripts(arguments.ensembl_gene_id)
                print(transcript_result.model_dump_json())
                return
            if arguments.command == "import-gene":
                api_key = (
                    settings.ncbi_api_key.get_secret_value().strip()
                    if settings.ncbi_api_key
                    else ""
                )
                transport = RetryingJsonClient(
                    client,
                    provider="NCBI Gene",
                    max_attempts=settings.external_api_max_attempts,
                    backoff_seconds=settings.external_api_backoff_seconds,
                )
                gene_provider = NcbiGeneAdapter(
                    transport,
                    base_url=settings.ncbi_base_url,
                    tool=settings.ncbi_tool,
                    email=settings.ncbi_email,
                    api_key=api_key or None,
                )
                with get_session_factory()() as session:
                    result = GeneIngestionService(session, gene_provider).import_gene(
                        arguments.symbol, arguments.taxonomy_id
                    )
            elif arguments.command == "import-publication":
                transport = RetryingJsonClient(
                    client,
                    provider="NCBI PubMed",
                    max_attempts=settings.external_api_max_attempts,
                    backoff_seconds=settings.external_api_backoff_seconds,
                )
                publication_provider = PubMedAdapter(
                    transport,
                    base_url=settings.ncbi_base_url,
                    tool=settings.ncbi_tool,
                    email=settings.ncbi_email,
                    api_key=settings.ncbi_api_key.get_secret_value()
                    if settings.ncbi_api_key
                    else None,
                )
                with get_session_factory()() as session:
                    publication_result = PublicationIngestionService(
                        session, publication_provider
                    ).import_publication(arguments.pubmed_id)
                print(publication_result.model_dump_json())
                return
            else:
                transport = RetryingJsonClient(
                    client,
                    provider="UniProt",
                    max_attempts=settings.external_api_max_attempts,
                    backoff_seconds=settings.external_api_backoff_seconds,
                )
                protein_provider = UniProtAdapter(transport, base_url=settings.uniprot_base_url)
                with get_session_factory()() as session:
                    result = ProteinIngestionService(session, protein_provider).import_protein(
                        arguments.accession
                    )
    except (IntegrationError, IngestionPersistenceError, ApplicationError, ValueError) as exc:
        code = getattr(exc, "code", "ingestion_error")
        print(json.dumps({"error": {"code": code, "message": str(exc)}}), file=sys.stderr)
        raise SystemExit(1) from exc
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
