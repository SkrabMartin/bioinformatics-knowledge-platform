"""Synthetic Ensembl contracts, confined to isolated test databases."""

from copy import deepcopy

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.errors import IngestionPersistenceError
from app.ingestion.transcripts import TranscriptIngestionService
from app.integrations.ensembl import EnsemblTranscriptAdapter
from app.integrations.errors import UpstreamResponseError
from app.integrations.http import RetryingJsonClient
from app.models import Gene, Organism, Transcript
from app.schemas.gene import GeneUpdate
from app.services.entities import GeneService
from app.services.errors import ConflictError

GENE = "ENSG00000000001"
TRANSCRIPT = "ENST00000000001"


def payload() -> dict:
    return {
        "id": GENE,
        "object_type": "Gene",
        "db_type": "core",
        "species": "synthetic_species",
        "assembly_name": "DEMO-ASSEMBLY",
        "seq_region_name": "DEMO",
        "start": 100,
        "end": 1000,
        "strand": -1,
        "Transcript": [
            {
                "id": TRANSCRIPT,
                "object_type": "Transcript",
                "Parent": GENE,
                "species": "synthetic_species",
                "assembly_name": "DEMO-ASSEMBLY",
                "seq_region_name": "DEMO",
                "start": 200,
                "end": 500,
                "strand": -1,
                "version": 1,
                "display_name": "Synthetic transcript",
                "biotype": "test-only",
            }
        ],
    }


def metadata() -> dict:
    return {
        "species": [
            {
                "name": "synthetic_species",
                "assembly": "DEMO-ASSEMBLY",
                "taxon_id": 999999,
                "release": 116,
            }
        ]
    }


def provider(gene: dict | None = None, species: dict | None = None) -> EnsemblTranscriptAdapter:
    class Http:
        def get_json(self, url: str, **_kwargs: object) -> dict:
            return (gene or payload()) if "/lookup/" in url else (species or metadata())

    return EnsemblTranscriptAdapter(Http(), base_url="https://example.test")


def seed_gene(session: Session) -> Gene:
    organism = Organism(
        scientific_name="Synthetic organism", taxonomy_id="999999", source="development_fixture"
    )
    session.add(organism)
    session.flush()
    gene = Gene(
        symbol="DEMO-TRANSCRIPT",
        name="Synthetic gene",
        organism_id=organism.id,
        ensembl_gene_id=GENE,
        source="development_fixture",
    )
    session.add(gene)
    session.commit()
    return gene


def test_adapter_uses_explicit_parent_taxonomy_assembly_and_release() -> None:
    requests: list[httpx2.Request] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200, json=payload() if "/lookup/" in request.url.path else metadata()
        )

    with httpx2.Client(transport=httpx2.MockTransport(respond)) as client:
        transport = RetryingJsonClient(
            client, provider="Ensembl", max_attempts=1, backoff_seconds=0
        )
        batch = EnsemblTranscriptAdapter(
            transport, base_url="https://example.test"
        ).fetch_transcripts(GENE)
    assert len(requests) == 2
    assert requests[0].url.params["expand"] == "1"
    assert batch.taxonomy_id == "999999" and batch.source_release == "116"
    record = batch.transcripts[0]
    assert record.strand == "-" and record.start_position == 200
    assert record.assembly_name == "DEMO-ASSEMBLY"


@pytest.mark.parametrize(
    "field,value",
    [
        ("Parent", "ENSG00000000002"),
        ("species", "other_species"),
        ("assembly_name", "OTHER-ASSEMBLY"),
        ("seq_region_name", "OTHER"),
        ("strand", 1),
        ("start", 0),
        ("start", True),
        ("start", 50),
        ("end", 1001),
        ("version", False),
        ("object_type", "Protein"),
        ("id", "../invalid"),
    ],
)
def test_invalid_source_transcripts_reject_the_whole_batch(field: str, value: object) -> None:
    raw = payload()
    raw["Transcript"][0][field] = value
    with pytest.raises(UpstreamResponseError):
        provider(raw).fetch_transcripts(GENE)


def test_missing_oversized_or_duplicate_annotations_fail_closed() -> None:
    for value in (None, [{}] * 201, payload()["Transcript"] * 2):
        raw = payload()
        raw["Transcript"] = value
        with pytest.raises(UpstreamResponseError):
            provider(raw).fetch_transcripts(GENE)


def test_ambiguous_species_and_assembly_metadata_fail_closed() -> None:
    raw = metadata()
    raw["species"] *= 2
    with pytest.raises(UpstreamResponseError):
        provider(species=raw).fetch_transcripts(GENE)
    raw = metadata()
    raw["species"][0]["assembly"] = "OTHER"
    with pytest.raises(UpstreamResponseError):
        provider(species=raw).fetch_transcripts(GENE)


def test_import_is_idempotent_and_retains_absent_observations(session: Session) -> None:
    gene = seed_gene(session)
    service = TranscriptIngestionService(session, provider())
    assert service.import_transcripts(GENE).created == 1
    assert service.import_transcripts(GENE).unchanged == 1
    raw = payload()
    raw["Transcript"] = []
    result = TranscriptIngestionService(session, provider(raw)).import_transcripts(GENE)
    assert result.created == result.updated == result.unchanged == 0
    transcript = session.scalar(select(Transcript))
    assert transcript is not None and transcript.gene_id == gene.id
    assert transcript.source == "Ensembl" and transcript.source_identifier == TRANSCRIPT
    assert transcript.source_release == "116"


def test_missing_local_gene_and_wrong_taxonomy_do_not_create_entities(session: Session) -> None:
    with pytest.raises(IngestionPersistenceError):
        TranscriptIngestionService(session, provider()).import_transcripts(GENE)
    gene = seed_gene(session)
    species = metadata()
    species["species"][0]["taxon_id"] = 1
    with pytest.raises(IngestionPersistenceError):
        TranscriptIngestionService(session, provider(species=species)).import_transcripts(GENE)
    assert session.scalar(select(func.count()).select_from(Transcript)) == 0
    assert session.get(Gene, gene.id) is not None


def test_version_update_and_regression_are_explicit(session: Session) -> None:
    seed_gene(session)
    TranscriptIngestionService(session, provider()).import_transcripts(GENE)
    raw = payload()
    raw["Transcript"][0]["version"] = 2
    assert TranscriptIngestionService(session, provider(raw)).import_transcripts(GENE).updated == 1
    with pytest.raises(IngestionPersistenceError):
        TranscriptIngestionService(session, provider()).import_transcripts(GENE)
    assert session.scalar(select(Transcript.version)) == 2


def test_gene_identity_edits_are_rejected_when_transcripts_exist(session: Session) -> None:
    gene = seed_gene(session)
    TranscriptIngestionService(session, provider()).import_transcripts(GENE)
    with pytest.raises(ConflictError):
        GeneService(session).update(gene.id, GeneUpdate(ensembl_gene_id="ENSG00000000002"))
    with pytest.raises(ConflictError):
        GeneService(session).update(gene.id, GeneUpdate(ensembl_gene_id=None))


def test_cross_gene_identity_conflict_rolls_back_new_records(session: Session) -> None:
    seed_gene(session)
    TranscriptIngestionService(session, provider()).import_transcripts(GENE)
    original = session.scalar(select(Transcript))
    assert original is not None
    other = Gene(
        symbol="DEMO-OTHER",
        name="Other synthetic gene",
        organism_id=original.gene.organism_id,
        ensembl_gene_id="ENSG00000000002",
        source="development_fixture",
    )
    session.add(other)
    session.commit()
    raw = payload()
    raw["id"] = other.ensembl_gene_id
    first = deepcopy(raw["Transcript"][0])
    first["id"] = "ENST00000000002"
    raw["Transcript"] = [first, raw["Transcript"][0]]
    for record in raw["Transcript"]:
        record["Parent"] = raw["id"]
    with pytest.raises(IngestionPersistenceError):
        TranscriptIngestionService(session, provider(raw)).import_transcripts(raw["id"])
    assert session.scalar(select(func.count()).select_from(Transcript)) == 1


def test_transcript_read_api_pagination_filtering_and_gene_context(
    client: TestClient, session: Session
) -> None:
    gene = seed_gene(session)
    TranscriptIngestionService(session, provider()).import_transcripts(GENE)
    response = client.get("/api/v1/transcripts?page_size=1")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert client.get("/api/v1/transcripts?q=" + TRANSCRIPT + ".1").json()["total"] == 1
    assert client.get("/api/v1/transcripts?q=%25").json()["total"] == 0
    detail = client.get("/api/v1/transcripts/by-ensembl/" + TRANSCRIPT).json()
    assert detail["gene_id"] == gene.id and detail["source"] == "Ensembl"
    assert detail["assembly_name"] == "DEMO-ASSEMBLY"
    assert client.get("/api/v1/transcripts/by-ensembl/ABSENT").status_code == 404
    assert client.get("/api/v1/transcripts?page_size=101").status_code == 422
    gene_detail = client.get("/api/v1/genes/by-symbol/DEMO-TRANSCRIPT?taxonomy_id=999999").json()
    assert gene_detail["transcripts"][0]["ensembl_transcript_id"] == TRANSCRIPT
