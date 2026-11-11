"""Synthetic stored records only; these tests never populate the public site."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BiologicalProcess,
    Disease,
    Gene,
    MolecularFunction,
    Organism,
    Pathway,
    Transcript,
    Variant,
)
from app.schemas.search import SearchEntityType
from app.search import SearchService


def seed(session: Session) -> None:
    organism = Organism(
        scientific_name="Synthetic search organism", taxonomy_id="999999", source="test_source"
    )
    session.add(organism)
    session.flush()
    gene = Gene(
        symbol="TEST", name="Synthetic parent", organism_id=organism.id, source="test_source"
    )
    session.add(gene)
    session.flush()
    session.add_all(
        [
            Transcript(
                gene_id=gene.id,
                ensembl_transcript_id="ENST00000000001",
                version=7,
                name="Synthetic shared transcript",
                biotype="synthetic_biotype",
                assembly_name="TEST-ASSEMBLY",
                sequence_region="TEST",
                start_position=1,
                end_position=20,
                strand="+",
                source="Ensembl",
                source_release="TEST",
                source_identifier="ENST00000000001",
            ),
            Disease(
                name="Synthetic shared disease",
                mondo_id="MONDO:TEST",
                disease_ontology_id="DOID:TEST",
                source="test_source",
            ),
            Variant(
                rsid="rsTEST",
                hgvs="TEST:g.1A>C",
                description="Synthetic shared variant",
                organism_id=organism.id,
                source="test_source",
            ),
            Variant(hgvs="TEST:g.2A>C", organism_id=organism.id, source="test_source"),
            Pathway(
                name="Synthetic shared pathway",
                source_identifier="TEST-PATHWAY",
                source="test_source",
                source_release="TEST",
            ),
            BiologicalProcess(
                go_id="GO:0000001",
                name="Synthetic shared process",
                source="test_source",
                source_identifier="GO:0000001",
                source_release="TEST",
            ),
            MolecularFunction(
                go_id="GO:0000002",
                name="Synthetic shared function",
                source="test_source",
                source_identifier="GO:0000002",
                source_release="TEST",
            ),
        ]
    )
    session.commit()


def search(session: Session, query: str, **kwargs):
    return SearchService(session).search(query, page=1, page_size=100, **kwargs)


def test_six_catalogues_join_shared_search_without_duplicates_or_kind_leaks(
    session: Session,
) -> None:
    seed(session)
    result = search(session, "shared")
    assert result.total == result.counts.total == 6
    assert {item.entity_type for item in result.items} == {
        SearchEntityType.TRANSCRIPT,
        SearchEntityType.DISEASE,
        SearchEntityType.VARIANT,
        SearchEntityType.PATHWAY,
        SearchEntityType.BIOLOGICAL_PROCESS,
        SearchEntityType.MOLECULAR_FUNCTION,
    }
    assert result.counts.biological_process == result.counts.molecular_function == 1
    assert len({(item.entity_type, item.entity_id) for item in result.items}) == 6
    for item in result.items:
        assert item.href is not None and item.source in {"test_source", "Ensembl"}
    pathway = next(item for item in result.items if item.entity_type == "pathway")
    assert pathway.organism is None
    transcript = next(item for item in result.items if item.entity_type == "transcript")
    assert transcript.organism.taxonomy_id == "999999"
    assert transcript.href == "/transcript/ENST00000000001"


def test_identifiers_versions_and_link_targets(session: Session) -> None:
    seed(session)
    for query, kind, route in [
        ("ENST00000000001.7", "transcript", "/transcript/ENST00000000001"),
        ("MONDO:TEST", "disease", "/disease/"),
        ("DOID:TEST", "disease", "/disease/"),
        ("TEST:g.2A>C", "variant", "/variant/"),
        ("TEST-PATHWAY", "pathway", "/pathway/"),
        ("GO:0000001", "biological_process", "/biological-process/"),
        ("GO:0000002", "molecular_function", "/molecular-function/"),
    ]:
        result = search(session, query, entity_types=[SearchEntityType(kind)])
        assert result.total == 1
        assert result.items[0].score >= 1300
        assert result.items[0].href.startswith(route)
        assert result.items[0].matched_fields
    assert (
        search(session, "ENST00000000001.999", entity_types=[SearchEntityType.TRANSCRIPT]).total
        == 0
    )


def test_related_parent_ranking_filters_and_suggestions(session: Session) -> None:
    seed(session)
    result = search(session, "TEST")
    assert result.items[0].entity_type == "gene"
    transcript = search(session, "TEST", entity_types=[SearchEntityType.TRANSCRIPT])
    assert transcript.total == 1 and transcript.counts.total > transcript.total
    assert any(field.field == "gene_symbol" for field in transcript.items[0].matched_fields)
    suggestions = SearchService(session).suggestions("ENST00000000001", limit=2)
    assert suggestions.items[0].entity_type == "transcript"
    assert suggestions.items[0].href == "/transcript/ENST00000000001"


def test_new_filters_are_valid_and_empty_catalogues_are_honest(client: TestClient) -> None:
    for kind in [
        "transcript",
        "disease",
        "variant",
        "pathway",
        "biological_process",
        "molecular_function",
    ]:
        response = client.get("/api/v1/search", params={"q": "absent", "type": kind})
        assert response.status_code == 200 and response.json()["total"] == 0
    assert client.get("/api/v1/search", params={"q": "TEST", "type": "invented"}).status_code == 422


def test_literal_wildcards_and_multi_term_matching(session: Session) -> None:
    seed(session)
    assert search(session, "%").total == 0
    underscore = search(session, "_")
    assert underscore.total == 1 and underscore.items[0].entity_type == "transcript"
    assert (
        search(session, "shared transcript", entity_types=[SearchEntityType.TRANSCRIPT]).total == 1
    )
    assert session.scalar(select(Gene.symbol)) == "TEST"


def test_search_budget_returns_safe_error_instead_of_partial_results(session: Session) -> None:
    from unittest.mock import patch

    import pytest

    from app.search.service import SearchTimeout

    with (
        patch("app.search.service.time.monotonic", side_effect=[0, 6]),
        pytest.raises(SearchTimeout),
    ):
        search(session, "anything")
