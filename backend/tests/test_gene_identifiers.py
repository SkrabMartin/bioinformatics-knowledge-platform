"""Synthetic identifier assertions: tests do not import scientific records into the site."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.identifiers import canonical_gene_identifier
from app.ingestion.errors import IngestionPersistenceError
from app.ingestion.identifier_models import NormalizedGeneIdentifier
from app.ingestion.models import NormalizedProtein
from app.ingestion.services import GeneIngestionService, ProteinIngestionService
from app.integrations.errors import UpstreamResponseError
from app.integrations.uniprot.client import UniProtAdapter
from app.models import Gene, GeneExternalIdentifier, GeneIdentifierEvidence, Organism, Protein
from app.schemas.gene import GeneUpdate
from app.services.entities import GeneService
from app.services.errors import ConflictError
from tests.test_ingestion import FakeGeneProvider, FakeProteinProvider

ENSEMBL = "ENSG00000141510"


def mapped_record() -> NormalizedProtein:
    return (
        FakeProteinProvider()
        .fetch_protein("P04637")
        .model_copy(
            update={
                "gene_identifiers": [
                    NormalizedGeneIdentifier(
                        namespace="ensembl_gene",
                        accession=ENSEMBL,
                        reported_accession=ENSEMBL + ".20",
                    )
                ],
                "source_record_version": "42",
            }
        )
    )


class MappedProvider:
    def __init__(self, record: NormalizedProtein | None = None) -> None:
        self.record = record or mapped_record()

    def fetch_protein(self, _accession: str) -> NormalizedProtein:
        return self.record


def seed(session: Session) -> int:
    return GeneIngestionService(session, FakeGeneProvider()).import_gene("TP53").entity_id


def raw_protein() -> dict:
    return {
        "primaryAccession": "P04637",
        "organism": {"taxonId": 9606, "scientificName": "Synthetic test organism"},
        "proteinDescription": {"recommendedName": {"fullName": {"value": "Synthetic protein"}}},
        "entryAudit": {"entryVersion": 42},
        "uniProtKBCrossReferences": [
            {"database": "GeneID", "id": "7157"},
            {
                "database": "Ensembl",
                "id": "ENST00000269305.9",
                "properties": [
                    {"key": "GeneId", "value": ENSEMBL + ".20"},
                ],
            },
        ],
    }


class UnusedHttp:
    def get_json(self, *_args: object, **_kwargs: object) -> dict:
        raise AssertionError("No live HTTP in these contracts")


def test_uniprot_explicit_mapping_retains_source_version_and_reported_identity() -> None:
    record = UniProtAdapter(UnusedHttp(), base_url="https://example.test")._normalize(
        raw_protein(), "P04637"
    )
    assert record.gene_identifiers[0].accession == ENSEMBL
    assert record.gene_identifiers[0].reported_accession == ENSEMBL + ".20"
    assert record.source_record_version == "42"


@pytest.mark.parametrize(
    "namespace,reported,expected",
    [
        ("ncbi_gene", "7157", "7157"),
        ("ensembl_gene", ENSEMBL, ENSEMBL),
        ("ensembl_gene", ENSEMBL + ".20", ENSEMBL),
    ],
)
def test_identifier_namespace_normalization(namespace: str, reported: str, expected: str) -> None:
    assert canonical_gene_identifier(namespace, reported) == expected


@pytest.mark.parametrize(
    "namespace,reported",
    [
        ("ncbi_gene", ENSEMBL),
        ("ensembl_gene", "7157"),
        ("alias", "TP53"),
        ("ncbi_gene", "0"),
        ("ncbi_gene", "../7157"),
        ("ensembl_gene", ENSEMBL + ".0"),
    ],
)
def test_untyped_or_malformed_identifiers_are_rejected(namespace: str, reported: str) -> None:
    with pytest.raises(ValueError):
        canonical_gene_identifier(namespace, reported)


def test_contradictory_normalized_assertion_is_rejected() -> None:
    with pytest.raises(ValidationError):
        NormalizedGeneIdentifier(
            namespace="ensembl_gene", accession=ENSEMBL, reported_accession="ENSG00000000001.1"
        )


@pytest.mark.parametrize(
    "reference",
    [
        {"database": "GeneID", "id": "1"},
        {"database": "Ensembl", "properties": [{"key": "GeneId", "value": "ENSG00000000001.1"}]},
        {"database": "Ensembl", "properties": [{"key": "GeneId", "value": "../invalid"}]},
    ],
)
def test_ambiguous_or_invalid_source_mappings_fail_closed(reference: dict) -> None:
    raw = raw_protein()
    raw["uniProtKBCrossReferences"].append(reference)
    with pytest.raises(UpstreamResponseError):
        UniProtAdapter(UnusedHttp(), base_url="https://example.test")._normalize(raw, "P04637")


def test_registry_identity_and_independent_source_assertions_are_idempotent(
    session: Session,
) -> None:
    gene_id = seed(session)
    importer = ProteinIngestionService(session, MappedProvider())
    assert importer.import_protein("P04637").action == "created"
    assert importer.import_protein("P04637").action == "unchanged"
    gene = session.get(Gene, gene_id)
    assert gene is not None and gene.ensembl_gene_id == ENSEMBL and gene.source == "NCBI Gene"
    assert session.scalar(select(func.count()).select_from(GeneExternalIdentifier)) == 2
    assert session.scalar(select(func.count()).select_from(GeneIdentifierEvidence)) == 3
    evidence = session.scalar(
        select(GeneIdentifierEvidence).where(
            GeneIdentifierEvidence.reported_accession == ENSEMBL + ".20"
        )
    )
    assert evidence is not None and evidence.source == "UniProt"
    assert evidence.source_identifier == "P04637" and evidence.source_record_version == "42"


def test_primary_identity_and_organism_edits_are_blocked(session: Session) -> None:
    gene_id = seed(session)
    for update in (GeneUpdate(ncbi_gene_id=None), GeneUpdate(ncbi_gene_id="1")):
        with pytest.raises(ConflictError):
            GeneService(session).update(gene_id, update)
    other = Organism(scientific_name="Another synthetic organism", source="development_fixture")
    session.add(other)
    session.commit()
    with pytest.raises(ConflictError):
        GeneService(session).update(gene_id, GeneUpdate(organism_id=other.id))


def test_symbol_fallback_cannot_manufacture_external_identifier_evidence(session: Session) -> None:
    seed(session)
    record = mapped_record().model_copy(update={"ncbi_gene_id": None})
    ProteinIngestionService(session, MappedProvider(record)).import_protein("P04637")
    assert session.scalar(select(Gene.ensembl_gene_id)) is None
    assert session.scalar(select(func.count()).select_from(GeneIdentifierEvidence)) == 1


def test_unknown_explicit_ncbi_identity_does_not_fall_back_to_symbol(session: Session) -> None:
    seed(session)
    record = mapped_record().model_copy(update={"ncbi_gene_id": "1"})
    ProteinIngestionService(session, MappedProvider(record)).import_protein("P04637")
    assert session.scalar(select(Protein.gene_id)) is None
    assert session.scalar(select(func.count()).select_from(GeneExternalIdentifier)) == 1


def test_namespace_collision_does_not_merge_genes(session: Session) -> None:
    organism = Organism(
        scientific_name="Human test", taxonomy_id="9606", source="development_fixture"
    )
    session.add(organism)
    session.flush()
    session.add(
        Gene(
            symbol="DEMO-OTHER",
            name="Synthetic",
            organism_id=organism.id,
            ensembl_gene_id="7157",
            source="development_fixture",
        )
    )
    session.commit()
    seed(session)
    assert session.scalar(select(func.count()).select_from(Gene)) == 2


def test_identifier_conflict_rolls_back_protein_and_partial_evidence(session: Session) -> None:
    gene_id = seed(session)
    gene = session.get(Gene, gene_id)
    assert gene is not None
    gene.ensembl_gene_id = "ENSG00000000001"
    session.commit()
    with pytest.raises(IngestionPersistenceError):
        ProteinIngestionService(session, MappedProvider()).import_protein("P04637")
    assert session.scalar(select(func.count()).select_from(Protein)) == 0
    assert session.scalar(select(func.count()).select_from(GeneIdentifierEvidence)) == 1


def test_evidence_bound_rolls_back_import(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(session)
    monkeypatch.setattr("app.ingestion.gene_identifiers.MAX_IDENTIFIER_EVIDENCE", 1)
    with pytest.raises(IngestionPersistenceError):
        ProteinIngestionService(session, MappedProvider()).import_protein("P04637")
    assert session.scalar(select(func.count()).select_from(Protein)) == 0


def test_explicit_resolver_and_detail_show_observed_versions_only(
    client: TestClient, session: Session
) -> None:
    seed(session)
    ProteinIngestionService(session, MappedProvider()).import_protein("P04637")
    base = "/api/v1/genes/by-identifier/"
    result = client.get(base + "ensembl_gene/" + ENSEMBL + ".20")
    assert result.status_code == 200, result.text
    assert result.json()["symbol"] == "TP53" and len(result.json()["external_identifiers"]) == 2
    assert client.get(base + "ensembl_gene/" + ENSEMBL + ".999").status_code == 404
    assert client.get(base + "ncbi_gene/7157").status_code == 200
    assert client.get(base + "alias/TP53").status_code == 422
    assert client.get(base + "ncbi_gene/TP53").status_code == 422


def test_gene_refresh_cannot_replace_registered_ensembl_identity(session: Session) -> None:
    gene_id = seed(session)
    ProteinIngestionService(session, MappedProvider()).import_protein("P04637")

    class ConflictingGeneProvider(FakeGeneProvider):
        def fetch_gene(self, symbol: str, taxonomy_id: str = "9606"):
            return (
                super()
                .fetch_gene(symbol, taxonomy_id)
                .model_copy(update={"ensembl_gene_id": "ENSG00000000001"})
            )

    with pytest.raises(IngestionPersistenceError, match="source-backed"):
        GeneIngestionService(session, ConflictingGeneProvider()).import_gene("TP53")
    assert session.get(Gene, gene_id).ensembl_gene_id == ENSEMBL
