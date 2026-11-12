"""Synthetic GO labels and proteins; no authoritative biological assertions."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.models import MolecularFunction, Organism, Protein, ProteinCellularComponent
from app.schemas.graph import GraphLimits
from app.schemas.ontology import AnnotationCreate, ParentCreate, TermCreate
from app.schemas.search import SearchEntityType
from app.search import SearchService
from app.services.errors import ConflictError, NotFoundError
from app.services.graph import GraphService
from app.services.ontology import KnowledgeService
from app.services.relationships import RelationshipService


def source(identifier: str = "TEST:assertion") -> dict:
    return {
        "source": "development_fixture",
        "source_identifier": identifier,
        "source_release": "TEST-1",
        "source_url": "https://example.test/annotation",
    }


def seed(session: Session):
    organism = Organism(
        scientific_name="Synthetic organism", taxonomy_id="999999", source="development_fixture"
    )
    session.add(organism)
    session.flush()
    protein = Protein(
        accession="TEST-PROTEIN",
        name="Synthetic protein",
        organism_id=organism.id,
        source="development_fixture",
    )
    session.add(protein)
    session.commit()
    service = KnowledgeService(session)
    terms = []
    for number, kind in [
        (9999901, "cellular_component"),
        (9999902, "cellular_component"),
        (9999903, "molecular_function"),
    ]:
        terms.append(
            service.create_term(
                TermCreate.model_validate(
                    {
                        "kind": kind,
                        "go_id": f"GO:{number}",
                        "name": f"Synthetic shared {number}",
                        **source(str(number)),
                    }
                )
            )
        )
    return protein, terms[0], terms[1], terms[2]


def test_cellular_component_browsing_search_and_aspect_separation(session: Session) -> None:
    _, child, _, function = seed(session)
    service = KnowledgeService(session)
    assert service.browse("cellular_component", page=1, page_size=1, query=None).total == 2
    assert service.browse("molecular_function", page=1, page_size=20, query=None).total == 1
    with pytest.raises(NotFoundError):
        service.get("cellular_component", function.id)
    result = SearchService(session).search(
        child.go_id, page=1, page_size=20, entity_types=[SearchEntityType.CELLULAR_COMPONENT]
    )
    assert result.total == 1 and result.items[0].href == f"/cellular-component/{child.id}"
    shared = SearchService(session).search("shared", page=1, page_size=20)
    assert shared.counts.cellular_component == 2 and shared.counts.molecular_function == 1
    assert (
        SearchService(session).suggestions(child.go_id, limit=2).items[0].entity_type
        == "cellular_component"
    )


def test_source_assertions_and_hierarchy_are_exposed_in_both_directions_and_graph(
    session: Session,
) -> None:
    protein, child, parent, _ = seed(session)
    service = KnowledgeService(session)
    assertion = service.annotate(
        "cellular_component",
        child.id,
        AnnotationCreate.model_validate(
            {
                "entity_id": protein.id,
                "evidence_kind": "curated",
                "evidence_code": "IDA",
                **source(),
            }
        ),
    )
    assert assertion.relationship_type == "protein_cellular_component"
    assert (
        assertion.predicate == "annotated_to"
        and assertion.object.entity_type == "cellular_component"
    )
    assert assertion.source_release == "TEST-1" and assertion.evidence_code == "IDA"
    hierarchy = service.add_parent(
        "cellular_component",
        child.id,
        ParentCreate.model_validate({"parent_id": parent.id, **source("TEST:parent")}),
    )
    assert (
        hierarchy.relationship_type == "cellular_component_parent" and hierarchy.predicate == "is_a"
    )
    relations = RelationshipService(session)
    assert relations.list_for("protein", protein.id, page=1, page_size=20).total == 1
    assert relations.list_for("cellular_component", child.id, page=1, page_size=20).total == 2
    graph = GraphService(session).explore("protein", protein.id, limits=GraphLimits(depth=2))
    assert {edge.assertion.relationship_type for edge in graph.edges} == {
        "protein_cellular_component",
        "cellular_component_parent",
    }
    assert len(graph.nodes) == 3
    filtered = GraphService(session).explore(
        "cellular_component",
        child.id,
        limits=GraphLimits(relationship_types=["cellular_component_parent"]),
    )
    assert len(filtered.edges) == 1
    # No propagated annotation from protein directly to the parent is fabricated.
    assert session.scalar(select(ProteinCellularComponent.term_id)) == child.id


def test_cross_aspect_cycles_duplicates_and_invalid_targets_fail_closed(session: Session) -> None:
    protein, child, parent, function = seed(session)
    service = KnowledgeService(session)
    data = AnnotationCreate.model_validate(
        {"entity_id": protein.id, "evidence_kind": "curated", **source()}
    )
    service.annotate("cellular_component", child.id, data)
    with pytest.raises(ConflictError):
        service.annotate("cellular_component", child.id, data)
    with pytest.raises(NotFoundError):
        service.annotate("cellular_component", function.id, data)
    service.add_parent(
        "cellular_component",
        child.id,
        ParentCreate.model_validate({"parent_id": parent.id, **source()}),
    )
    with pytest.raises(ConflictError):
        service.add_parent(
            "cellular_component",
            parent.id,
            ParentCreate.model_validate({"parent_id": child.id, **source()}),
        )
    with pytest.raises(NotFoundError):
        service.add_parent(
            "cellular_component",
            child.id,
            ParentCreate.model_validate({"parent_id": function.id, **source()}),
        )
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            ProteinCellularComponent(
                protein_id=protein.id,
                term_id=function.id,
                evidence_kind="curated",
                **source("TEST:wrong-aspect"),
            )
        )
        session.flush()
    assert isinstance(session.get(MolecularFunction, function.id), MolecularFunction)


def test_api_empty_state_and_protected_writes(client: TestClient) -> None:
    response = client.get("/api/v1/ontology/cellular_component")
    assert response.status_code == 200 and response.json()["total"] == 0
    payload = {
        "go_id": "GO:9999901",
        "kind": "cellular_component",
        "name": "Synthetic component",
        **source(),
    }
    assert client.post("/api/v1/ontology", json=payload).status_code in {401, 503}
    client.app.dependency_overrides[require_admin] = lambda: None
    try:
        created = client.post("/api/v1/ontology", json=payload)
        assert created.status_code == 201
        identifier = created.json()["id"]
        assert client.get(f"/api/v1/ontology/cellular_component/{identifier}").status_code == 200
        assert (
            client.get(f"/api/v1/relationships/cellular_component/{identifier}").status_code == 200
        )
        assert client.get(f"/api/v1/graph/cellular_component/{identifier}").status_code == 200
        assert (
            client.post(
                f"/api/v1/ontology/cellular_component/{identifier}/annotations",
                json={"entity_id": 1, "evidence_kind": "curated", "qualifier": "NOT", **source()},
            ).status_code
            == 422
        )
    finally:
        client.app.dependency_overrides.pop(require_admin)
