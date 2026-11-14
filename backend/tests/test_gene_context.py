"""Synthetic gene context contracts; no live scientific records are imported."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.models import NormalizedGene, NormalizedGeneLocation
from app.ingestion.services import GeneIngestionService, IngestionPersistenceError
from app.integrations.errors import UpstreamResponseError
from app.integrations.ncbi import NcbiGeneAdapter
from app.models import Gene, GeneAlias, GeneGenomicLocation, Organism
from app.schemas.gene import GeneUpdate
from app.search import SearchService
from app.services.entities import GeneService
from app.services.errors import ConflictError


class NoNetwork:
    def get_json(self, *_args: object, **_kwargs: object) -> dict[str, Any]:
        raise AssertionError("Synthetic contracts must not make live requests")


def summary(**overrides: object) -> dict[str, object]:
    return {
        "name": "DEMO-GENE",
        "description": "Synthetic gene, not scientific evidence",
        "organism": {"scientificname": "Synthetic organism", "taxid": 999999},
        "otheraliases": "DEMO-ALIAS, DEMO-GENE, DEMO-ALIAS",
        "genomicinfo": [
            {"chraccver": "DEMO_SEQ.1", "chrloc": "DEMO", "chrstart": 19, "chrstop": 9},
            {"chraccver": "DEMO_SEQ.2", "chrloc": "DEMO", "chrstart": 0, "chrstop": 2},
        ],
        **overrides,
    }


def normalized(**overrides: object) -> NormalizedGene:
    adapter = NcbiGeneAdapter(
        NoNetwork(), base_url="https://example.test", tool="test", email="test@example.org"
    )
    return adapter._normalize(summary(**overrides), "999999")


class Provider:
    def __init__(self, record: NormalizedGene | None = None) -> None:
        self.record = record or normalized()

    def fetch_gene(self, _symbol: str, taxonomy_id: str = "999999") -> NormalizedGene:
        return self.record


def import_gene(session: Session, record: NormalizedGene | None = None) -> int:
    return (
        GeneIngestionService(session, Provider(record)).import_gene("DEMO-GENE", "999999").entity_id
    )


def test_adapter_preserves_all_reference_placements_without_inventing_assembly() -> None:
    record = normalized()
    assert record.aliases == ["DEMO-ALIAS"]
    assert len(record.genomic_locations) == 2
    first, second = record.genomic_locations
    assert (first.start_position, first.end_position, first.strand) == (10, 20, "-")
    assert (second.start_position, second.end_position, second.strand) == (1, 3, "+")
    assert first.sequence_accession == "DEMO_SEQ.1"
    assert "assembly" not in first.model_dump()
    assert normalized(genomicinfo=[{"chrstart": 0, "chrstop": 10}]).genomic_locations == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"otheraliases": ["unexpected"]},
        {"otheraliases": "x" * 65},
        {"genomicinfo": "invalid"},
        {"genomicinfo": [{"chraccver": "DEMO", "chrstart": -1, "chrstop": 5}]},
        {"genomicinfo": [{"chraccver": "DEMO", "chrstart": True, "chrstop": 5}]},
        {"genomicinfo": [{"chraccver": "DEMO", "chrstart": 1, "chrstop": None}]},
        {"genomicinfo": [{}] * 101},
    ],
)
def test_malformed_context_fails_closed(overrides: dict[str, object]) -> None:
    with pytest.raises(UpstreamResponseError):
        normalized(**overrides)


def test_reimport_is_idempotent_and_preserves_missing_observations(session: Session) -> None:
    service = GeneIngestionService(session, Provider())
    first = service.import_gene("DEMO-GENE", "999999")
    assert service.import_gene("DEMO-GENE", "999999").action == "unchanged"
    assert session.scalar(select(func.count()).select_from(GeneAlias)) == 1
    assert session.scalar(select(func.count()).select_from(GeneGenomicLocation)) == 2
    import_gene(session, normalized(otheraliases="", genomicinfo=[]))
    assert session.scalar(select(func.count()).select_from(GeneAlias)) == 1
    assert session.scalar(select(func.count()).select_from(GeneGenomicLocation)) == 2
    alias = session.scalar(select(GeneAlias))
    assert alias is not None and alias.source_identifier == "999999"
    assert alias.source == "NCBI Gene" and alias.imported_at is not None
    assert GeneService(session).get(first.entity_id).id == first.entity_id


def test_new_context_changes_import_result_even_if_gene_projection_is_unchanged(
    session: Session,
) -> None:
    import_gene(session, normalized(otheraliases=""))
    result = GeneIngestionService(session, Provider()).import_gene("DEMO-GENE", "999999")
    assert result.action == "updated"


def test_alias_search_returns_canonical_gene_without_duplicate_rows(session: Session) -> None:
    gene_id = import_gene(session)
    session.add(
        GeneAlias(
            gene_id=gene_id,
            alias="DEMO-ALIAS-OTHER",
            source="development_fixture",
            source_identifier="demo-alias",
        )
    )
    session.commit()
    result = SearchService(session).search("demo-alias", page=1, page_size=20)
    assert result.total == 1
    assert result.items[0].primary_label == "DEMO-GENE"
    assert any(field.field == "alias" for field in result.items[0].matched_fields)
    assert result.items[0].href == "/gene/DEMO-GENE?taxonomy_id=999999"
    assert SearchService(session).search("%", page=1, page_size=20).total == 0


def test_aliases_do_not_merge_genes_and_can_match_mixed_terms(session: Session) -> None:
    import_gene(session)
    another = normalized(name="DEMO-SECOND").model_copy(update={"ncbi_gene_id": "999998"})
    import_gene(session, another)
    result = SearchService(session).search("DEMO-ALIAS", page=1, page_size=20)
    assert result.total == 2
    assert len({item.entity_id for item in result.items}) == 2
    assert SearchService(session).search("Synthetic DEMO-ALIAS", page=1, page_size=20).total == 2
    assert session.scalar(select(func.count()).select_from(Gene)) == 2


def test_taxonomy_change_is_rejected_for_source_observations(session: Session) -> None:
    gene_id = import_gene(session)
    other = Organism(scientific_name="Other synthetic organism", source="development_fixture")
    session.add(other)
    session.commit()
    with pytest.raises(ConflictError):
        GeneService(session).update(gene_id, GeneUpdate(organism_id=other.id))
    with pytest.raises(IngestionPersistenceError):
        GeneIngestionService(session, Provider()).import_gene("DEMO-GENE", "1")


def test_context_overflow_rolls_back_gene_and_annotations(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.ingestion.gene_context.MAX_CONTEXT_RECORDS", 1)
    with pytest.raises(IngestionPersistenceError):
        import_gene(session)
    assert session.scalar(select(func.count()).select_from(Gene)) == 0
    assert session.scalar(select(func.count()).select_from(GeneAlias)) == 0


def test_gene_detail_adds_sourced_context_without_changing_list_api(
    client: TestClient, session: Session
) -> None:
    gene_id = import_gene(session)
    detail = client.get("/api/v1/genes/by-symbol/DEMO-GENE?taxonomy_id=999999")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["aliases"][0]["alias"] == "DEMO-ALIAS"
    assert payload["genomic_locations"][0]["sequence_accession"] == "DEMO_SEQ.1"
    assert payload["genomic_locations"][0]["source_identifier"] == "999999"
    legacy = client.get(f"/api/v1/genes/{gene_id}").json()
    assert legacy["symbol"] == "DEMO-GENE" and "genomic_locations" not in legacy


def test_location_model_rejects_reversed_normalized_coordinates() -> None:
    with pytest.raises(ValidationError):
        NormalizedGeneLocation(
            sequence_accession="DEMO", start_position=2, end_position=1, strand="+"
        )
