"""Synthetic sourced graphs only; no asserted biological facts."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import (
    Disease,
    Gene,
    GeneDiseaseAssociation,
    Organism,
    Protein,
    ProteinInteraction,
    Publication,
    PublicationDisease,
    PublicationGene,
    PublicationProtein,
    Variant,
    VariantDiseaseAssociation,
    VariantGeneLocation,
)
from app.schemas.graph import GraphLimits
from app.services.graph import GraphService, GraphTimeoutError


def provenance(identifier: str) -> dict[str, str]:
    return {
        "source": "development_fixture",
        "source_identifier": identifier,
        "evidence_text": "Synthetic graph test; not scientific evidence.",
    }


def seed_graph(session: Session) -> dict[str, int]:
    organism = Organism(
        scientific_name="Demo organism", taxonomy_id="999999", source="development_fixture"
    )
    session.add(organism)
    session.flush()
    gene = Gene(
        symbol="DEMO", name="Test-only gene", organism_id=organism.id, source="development_fixture"
    )
    session.add(gene)
    session.flush()
    p1 = Protein(
        accession="DEMO-P1",
        name="Test-only protein",
        organism_id=organism.id,
        gene_id=gene.id,
        source="development_fixture",
        source_identifier="demo-protein",
    )
    p2 = Protein(
        accession="DEMO-P2",
        name="Test-only partner",
        organism_id=organism.id,
        source="development_fixture",
    )
    disease = Disease(name="Test-only disease", source="development_fixture")
    variant = Variant(hgvs="DEMO:variant", organism_id=organism.id, source="development_fixture")
    publication = Publication(
        doi="10.1234/graph-demo",
        title="Synthetic literature",
        authors=[],
        source="development_fixture",
    )
    session.add_all([p1, p2, disease, variant, publication])
    session.flush()
    session.add_all(
        [
            GeneDiseaseAssociation(gene_id=gene.id, disease_id=disease.id, **provenance("gd-a")),
            GeneDiseaseAssociation(gene_id=gene.id, disease_id=disease.id, **provenance("gd-b")),
            VariantGeneLocation(variant_id=variant.id, gene_id=gene.id, **provenance("vg")),
            VariantDiseaseAssociation(
                variant_id=variant.id, disease_id=disease.id, **provenance("vd")
            ),
            ProteinInteraction(protein_a_id=p1.id, protein_b_id=p1.id, **provenance("self")),
            ProteinInteraction(protein_a_id=p1.id, protein_b_id=p2.id, **provenance("partner")),
            PublicationGene(
                publication_id=publication.id,
                gene_id=gene.id,
                evidence_kind="structured_metadata",
                **provenance("pg"),
            ),
            PublicationProtein(
                publication_id=publication.id,
                protein_id=p1.id,
                evidence_kind="curated",
                **provenance("pp"),
            ),
            PublicationDisease(
                publication_id=publication.id,
                disease_id=disease.id,
                evidence_kind="curated",
                **provenance("pd"),
            ),
        ]
    )
    session.commit()
    return {
        "gene": gene.id,
        "protein": p1.id,
        "partner": p2.id,
        "disease": disease.id,
        "variant": variant.id,
        "publication": publication.id,
    }


def test_depth_identity_cycles_parallel_sources_and_boundary_edges(session: Session) -> None:
    ids = seed_graph(session)
    service = GraphService(session)
    first = service.explore("gene", ids["gene"], limits=GraphLimits(depth=1))
    deeper = service.explore("gene", ids["gene"], limits=GraphLimits(depth=3))
    assert len(first.nodes) == 5
    assert len(first.edges) == 9
    assert len(deeper.nodes) == 6
    assert len(deeper.edges) == 10
    assert len({node.id for node in deeper.nodes}) == 6
    assert len({edge.id for edge in deeper.edges}) == 10
    assert first.root_id == f"gene:{ids['gene']}"
    assert not first.truncated
    assert not deeper.truncated
    assert max(node.depth for node in deeper.nodes) == 2
    gd = [edge for edge in first.edges if edge.assertion.relationship_type == "gene_disease"]
    assert {edge.assertion.source_identifier for edge in gd} == {"gd-a", "gd-b"}
    self_edge = next(edge for edge in first.edges if edge.source_node == edge.target_node)
    assert not self_edge.directed
    assert self_edge.assertion.source == "development_fixture"
    encoding = next(edge for edge in first.edges if edge.assertion.predicate == "encodes")
    assert encoding.directed
    assert encoding.assertion.provenance_basis == "protein_record"
    assert encoding.assertion.source_identifier == "demo-protein"
    assert [(edge.id) for edge in deeper.edges] == [
        edge.id for edge in service.explore("gene", ids["gene"], limits=GraphLimits(depth=3)).edges
    ]


def test_graph_is_browsable_from_all_supported_types(session: Session) -> None:
    ids = seed_graph(session)
    for entity_type in ("gene", "protein", "disease", "variant", "publication"):
        result = GraphService(session).explore(
            entity_type, ids[entity_type], limits=GraphLimits(depth=2)
        )
        assert result.nodes[0].entity_type == entity_type
        assert result.edges
        assert all(
            edge.source_node in {node.id for node in result.nodes}
            and edge.target_node in {node.id for node in result.nodes}
            for edge in result.edges
        )


def test_limits_and_filters_never_traverse_hidden_bridges(session: Session) -> None:
    ids = seed_graph(session)
    service = GraphService(session)
    tiny = service.explore("gene", ids["gene"], limits=GraphLimits(max_nodes=1))
    assert len(tiny.nodes) == 1 and not tiny.edges
    assert "node_limit" in tiny.truncation_reasons
    limited = service.explore("gene", ids["gene"], limits=GraphLimits(depth=3, max_edges=2))
    assert len(limited.edges) == 2
    assert "edge_limit" in limited.truncation_reasons
    proteins = service.explore(
        "gene", ids["gene"], limits=GraphLimits(depth=3, entity_types=["protein"])
    )
    assert {node.entity_type for node in proteins.nodes} == {"gene", "protein"}
    disconnected = service.explore(
        "gene", ids["gene"], limits=GraphLimits(depth=3, relationship_types=["protein_interaction"])
    )
    assert len(disconnected.nodes) == 1 and not disconnected.edges


def test_candidate_scan_budget_is_bounded(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = seed_graph(session)
    monkeypatch.setattr("app.services.graph.MAX_SCANNED_EDGES", 4)
    graph = GraphService(session).explore("gene", ids["gene"], limits=GraphLimits(depth=3))
    assert graph.scanned_edges == 4
    assert "scan_limit" in graph.truncation_reasons


def test_graph_budget_before_root_is_error_after_root_is_partial(session: Session) -> None:
    ids = seed_graph(session)
    clock = Mock(side_effect=[0.0, 2.0])
    with pytest.raises(GraphTimeoutError):
        GraphService(session, clock=clock).explore("gene", ids["gene"], limits=GraphLimits())
    time = [0.0]
    service = GraphService(session, clock=lambda: time[0])
    original = service.repository.incident

    def expire(*args, **kwargs):
        result = original(*args, **kwargs)
        time[0] = 20.0
        return result

    service.repository.incident = expire
    graph = service.explore("gene", ids["gene"], limits=GraphLimits())
    assert len(graph.nodes) == 1 and not graph.edges
    assert graph.truncation_reasons == ["time_budget"]


def test_database_cancellation_is_partial_but_other_errors_propagate(session: Session) -> None:
    ids = seed_graph(session)

    class Cancelled(Exception):
        sqlstate = "57014"

    service = GraphService(session)
    service.repository.incident = Mock(side_effect=DBAPIError("SELECT", None, Cancelled()))
    graph = service.explore("gene", ids["gene"], limits=GraphLimits())
    assert graph.truncation_reasons == ["time_budget"]
    service.repository.incident = Mock(
        side_effect=DBAPIError("SELECT", None, RuntimeError("connection failed"))
    )
    with pytest.raises(DBAPIError):
        service.explore("gene", ids["gene"], limits=GraphLimits())


def test_graph_api_symbol_alias_validation_missing_root_and_isolation(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Contract equivalence must not depend on CI/desktop load; deadlines have separate tests.
    monkeypatch.setattr(
        "app.api.v1.graph.GraphService", lambda session: GraphService(session, clock=lambda: 0)
    )
    ids = seed_graph(session)
    symbol = client.get("/api/v1/graph/gene/by-symbol/DEMO", params={"taxonomy_id": "999999"})
    alias = client.get("/api/graph/gene/DEMO", params={"taxonomy_id": "999999"})
    assert symbol.status_code == 200
    assert alias.json() == symbol.json()
    assert symbol.json()["root_id"] == f"gene:{ids['gene']}"
    assert client.get("/api/v1/graph/gene/999999").status_code == 404
    for query in (
        {"depth": 4},
        {"max_nodes": 151},
        {"max_edges": 301},
        {"depth": 0},
        {"type": "drug"},
        {"relationship_type": "invented"},
    ):
        assert client.get(f"/api/v1/graph/gene/{ids['gene']}", params=query).status_code == 422
    assert client.get("/api/v1/graph/drug/1").status_code == 422
    isolated = Protein(
        accession="DEMO-isolated",
        name="Test-only isolated",
        organism_id=session.get(Gene, ids["gene"]).organism_id,
        source="development_fixture",
    )
    session.add(isolated)
    session.commit()
    response = client.get(f"/api/v1/graph/protein/{isolated.id}").json()
    assert len(response["nodes"]) == 1 and not response["edges"]
    assert not response["truncated"]
