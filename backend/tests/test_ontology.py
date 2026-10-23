"""Synthetic Phase 7 records only. These tests do not assert biological knowledge."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import BiologicalProcess, GeneBiologicalProcess, OntologyParent
from app.schemas.gene import GeneUpdate
from app.schemas.graph import GraphLimits
from app.schemas.ontology import AnnotationCreate, ParentCreate, PathwayCreate, TermCreate
from app.services.entities import GeneService
from app.services.errors import ConflictError, NotFoundError
from app.services.graph import GraphService
from app.services.ontology import KnowledgeService
from app.services.relationships import RelationshipService
from tests.test_graph import seed_graph


def source(identifier: str = "demo-assertion") -> dict[str, str]:
    return {
        "source": "development_fixture",
        "source_identifier": identifier,
        "source_release": "test-only-v1",
    }


def term(service: KnowledgeService, number: int, kind: str = "biological_process"):
    return service.create_term(
        TermCreate.model_validate(
            {
                "go_id": f"GO:{number:07}",
                "kind": kind,
                "name": f"Synthetic term {number}",
                **source(f"demo-term-{number}"),
            }
        )
    )


def test_term_identity_aspects_and_paginated_literal_filter(session: Session) -> None:
    service = KnowledgeService(session)
    bp = term(service, 9999901)
    term(service, 9999902, "molecular_function")
    term(service, 9999903)
    assert isinstance(bp, BiologicalProcess)
    assert service.browse("biological_process", page=2, page_size=1, query=None).total == 2
    assert service.browse("molecular_function", page=1, page_size=1, query=None).total == 1
    assert service.browse("biological_process", page=1, page_size=1, query="%").total == 0
    assert service.browse("biological_process", page=1, page_size=1, query=bp.go_id).total == 1
    with pytest.raises(NotFoundError):
        service.get("molecular_function", bp.id)
    with pytest.raises(ConflictError):
        term(service, 9999901, "molecular_function")


def test_new_schemas_reject_blank_ids_wrong_go_and_unsupported_negation() -> None:
    for overrides in (
        {"go_id": "GO:12"},
        {"name": " "},
        {"source_release": " "},
        {"source_identifier": " "},
        {"kind": "cellular_component"},
    ):
        with pytest.raises(ValidationError):
            TermCreate.model_validate(
                {
                    "go_id": "GO:9999999",
                    "kind": "biological_process",
                    "name": "Test-only",
                    **source(),
                    **overrides,
                }
            )
    with pytest.raises(ValidationError):
        AnnotationCreate.model_validate(
            {"entity_id": 1, "evidence_kind": "curated", "qualifier": "NOT", **source()}
        )
    with pytest.raises(ValidationError):
        PathwayCreate.model_validate(
            {"name": "Test-only", "source_url": "javascript:alert(1)", **source()}
        )


def test_direct_annotations_provenance_and_eight_type_graph(session: Session) -> None:
    ids = seed_graph(session)
    service = KnowledgeService(session)
    bp = term(service, 9999910)
    parent = term(service, 9999911)
    mf = term(service, 9999912, "molecular_function")
    pathway = service.create_pathway(
        PathwayCreate(name="Test-only pathway", **source("demo-pathway"))
    )
    for kind, target, entity in (
        ("pathway", pathway, ids["gene"]),
        ("biological_process", bp, ids["gene"]),
        ("molecular_function", mf, ids["protein"]),
    ):
        edge = service.annotate(
            kind,
            target.id,
            AnnotationCreate(
                entity_id=entity, evidence_kind="curated", evidence_code="EXP", **source()
            ),
        )
        assert edge.source_release == "test-only-v1" and edge.evidence_code == "EXP"
        assert edge.provenance_basis == "relationship_assertion"
        with pytest.raises(ConflictError):
            service.annotate(
                kind,
                target.id,
                AnnotationCreate(entity_id=entity, evidence_kind="curated", **source()),
            )
    service.add_parent("biological_process", bp.id, ParentCreate(parent_id=parent.id, **source()))
    for kind, identifier in (
        ("pathway", pathway.id),
        ("biological_process", bp.id),
        ("molecular_function", mf.id),
    ):
        assert (
            RelationshipService(session).list_for(kind, identifier, page=1, page_size=20).total > 0
        )
        assert (
            GraphService(session, clock=lambda: 0)
            .explore(kind, identifier, limits=GraphLimits(depth=1))
            .root_id
            == f"{kind}:{identifier}"
        )
    graph = GraphService(session, clock=lambda: 0).explore(
        "gene", ids["gene"], limits=GraphLimits(depth=3)
    )
    assert {"pathway", "biological_process", "molecular_function"} <= {
        node.entity_type for node in graph.nodes
    }
    hidden = GraphService(session, clock=lambda: 0).explore(
        "gene",
        ids["gene"],
        limits=GraphLimits(depth=3, entity_types=["gene", "molecular_function"]),
    )
    assert "molecular_function" not in {node.entity_type for node in hidden.nodes}


def test_hierarchy_is_dag_with_multiple_parents_no_cycles_or_cross_aspect(session: Session) -> None:
    service = KnowledgeService(session)
    a, b, c = [term(service, number) for number in (9999921, 9999922, 9999923)]
    mf = term(service, 9999924, "molecular_function")
    for child, parent in ((a, b), (a, c), (b, c)):
        assert (
            service.add_parent(
                "biological_process", child.id, ParentCreate(parent_id=parent.id, **source())
            ).predicate
            == "is_a"
        )
    for child, parent in ((c, a), (a, a)):
        with pytest.raises(ConflictError):
            service.add_parent(
                "biological_process", child.id, ParentCreate(parent_id=parent.id, **source())
            )
    with pytest.raises(NotFoundError):
        service.add_parent("biological_process", a.id, ParentCreate(parent_id=mf.id, **source()))
    assert len(service.repository.ancestors(a.id)) == 2


def test_database_rejects_wrong_aspect_and_self_parent_even_outside_service(
    session: Session,
) -> None:
    ids = seed_graph(session)
    service = KnowledgeService(session)
    mf = term(service, 9999931, "molecular_function")
    session.add(
        GeneBiologicalProcess(
            gene_id=ids["gene"],
            term_id=mf.id,
            kind="biological_process",
            evidence_kind="curated",
            **source(),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.add(
        OntologyParent(child_id=mf.id, parent_id=mf.id, kind="molecular_function", **source())
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_ancestor_limit_is_fail_closed(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    service = KnowledgeService(session)
    child, parent = term(service, 9999941), term(service, 9999942)
    monkeypatch.setattr(
        service.repository, "ancestors", lambda identifier: list(range(10000, 11001))
    )
    with pytest.raises(ConflictError, match="budget"):
        service.add_parent(
            "biological_process", child.id, ParentCreate(parent_id=parent.id, **source())
        )


def test_pathway_organism_and_gene_updates_preserve_existing_links(session: Session) -> None:
    from app.models import Gene, Organism

    ids = seed_graph(session)
    service = KnowledgeService(session)
    root = session.get(Gene, ids["gene"])
    assert root is not None
    gene = Gene(
        symbol="DEMO-PATHWAY-ONLY",
        name="Test-only gene without other links",
        organism_id=root.organism_id,
        source="development_fixture",
    )
    session.add(gene)
    session.commit()
    organism = Organism(scientific_name="Test-only second organism", source="development_fixture")
    session.add(organism)
    session.commit()
    incompatible = service.create_pathway(
        PathwayCreate(name="Test-only pathway", organism_id=organism.id, **source("demo-specific"))
    )
    with pytest.raises(ConflictError):
        service.annotate(
            "pathway",
            incompatible.id,
            AnnotationCreate(entity_id=gene.id, evidence_kind="curated", **source()),
        )
    neutral = service.create_pathway(
        PathwayCreate(name="Test-only neutral", **source("demo-neutral"))
    )
    service.annotate(
        "pathway",
        neutral.id,
        AnnotationCreate(entity_id=gene.id, evidence_kind="curated", **source()),
    )
    with pytest.raises(ConflictError):
        GeneService(session).update(gene.id, GeneUpdate(organism_id=organism.id))


def test_knowledge_api_admin_validation_pagination_and_empty_state(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.core.security.get_settings", lambda: Settings(_env_file=None, admin_api_token=None)
    )
    payload = {"name": "Test-only API pathway", **source("demo-api-pathway")}
    assert client.get("/api/v1/pathways").json()["total"] == 0
    assert client.post("/api/v1/pathways", json=payload).status_code == 503
    monkeypatch.setattr(
        "app.core.security.get_settings",
        lambda: Settings(_env_file=None, admin_api_token=SecretStr("test-only-token")),
    )
    assert client.post("/api/v1/pathways", json=payload).status_code == 401
    headers = {"Authorization": "Bearer test-only-token"}
    created = client.post("/api/v1/pathways", json=payload, headers=headers)
    assert created.status_code == 201
    assert (
        client.get(f"/api/v1/pathways/{created.json()['id']}").json()["source_release"]
        == "test-only-v1"
    )
    assert client.get("/api/v1/pathways?q=demo-api-pathway&page_size=1").json()["total"] == 1
    assert client.get("/api/v1/pathways?page_size=101").status_code == 422
    assert client.get("/api/v1/ontology/cellular_component").status_code == 422
    assert client.post("/api/v1/pathways", json=payload, headers=headers).status_code == 409
    bp = client.post(
        "/api/v1/ontology",
        json={
            "name": "Test-only process",
            "kind": "biological_process",
            "go_id": "GO:9999951",
            **source(),
        },
        headers=headers,
    )
    assert bp.status_code == 201
    assert client.get(f"/api/v1/graph/biological_process/{bp.json()['id']}").status_code == 200
    assert (
        client.get(f"/api/v1/relationships/biological_process/{bp.json()['id']}").json()["total"]
        == 0
    )
