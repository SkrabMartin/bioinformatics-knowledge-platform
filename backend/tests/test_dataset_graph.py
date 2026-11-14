"""Synthetic repository citations; no biological relationships inferred."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.integrations.geo import parse_geo_series
from app.models import DatasetPublication, Publication
from app.schemas.graph import GraphLimits
from app.services.datasets import DatasetService
from app.services.errors import ConflictError, NotFoundError
from app.services.graph import GraphService
from app.services.relationships import RelationshipService
from tests.test_datasets import SOFT


def seed(session):
    dataset, _ = DatasetService(session).save(parse_geo_series(SOFT, "GSE999999"))
    publication = Publication(
        pubmed_id="123456", title="Synthetic citation", source="development_fixture", authors=[]
    )
    session.add(publication)
    session.commit()
    return dataset, publication


def test_exact_pmid_resolution_graph_reverse_filters_and_bounds(session: Session) -> None:
    dataset, publication = seed(session)
    service = DatasetService(session)
    assert service.resolve_publications(dataset.id).created == 1
    again = service.resolve_publications(dataset.id)
    assert again.created == 0 and again.existing == 1 and not again.missing_pmids
    assert session.scalar(select(func.count()).select_from(DatasetPublication)) == 1
    for kind, identifier in [("dataset", dataset.id), ("publication", publication.id)]:
        rows = RelationshipService(session).list_for(kind, identifier, page=1, page_size=1)
        assert rows.total == 1
        edge = rows.items[0]
        assert edge.predicate == "cites" and edge.subject.entity_type == "dataset"
        assert edge.source_record_date == date(2020, 1, 2)
        assert edge.evidence_kind == "structured_metadata" and edge.source_identifier == "GSE999999"
        graph = GraphService(session).explore(kind, identifier, limits=GraphLimits())
        assert len(graph.nodes) == 2 and len(graph.edges) == 1 and not graph.truncated
        assert graph.edges[0].directed
    filtered = GraphService(session).explore(
        "dataset", dataset.id, limits=GraphLimits(relationship_types=["publication_gene"])
    )
    assert len(filtered.nodes) == 1 and not filtered.edges
    limited = GraphService(session).explore("dataset", dataset.id, limits=GraphLimits(max_nodes=1))
    assert limited.truncated and "node_limit" in limited.truncation_reasons
    assert not limited.edges


def test_missing_citations_and_titles_never_create_publications_or_links(session: Session) -> None:
    dataset, publication = seed(session)
    publication.pubmed_id = "999999"
    publication.title = dataset.title
    session.commit()
    result = DatasetService(session).resolve_publications(dataset.id)
    assert result.created == result.existing == 0 and result.missing_pmids == ["123456"]
    assert session.scalar(select(func.count()).select_from(Publication)) == 1
    assert session.scalar(select(func.count()).select_from(DatasetPublication)) == 0


def test_observed_citation_preserved_after_source_metadata_withdrawal(session: Session) -> None:
    dataset, _ = seed(session)
    service = DatasetService(session)
    service.resolve_publications(dataset.id)
    payload = parse_geo_series(SOFT, "GSE999999").model_copy(
        update={"publication_pmids": [], "source_updated_date": date(2021, 1, 1)}
    )
    service.save(payload, refresh=True)
    assert service.get(dataset.id).publication_pmids == []
    assert service.resolve_publications(dataset.id).created == 0
    edge = (
        RelationshipService(session).list_for("dataset", dataset.id, page=1, page_size=20).items[0]
    )
    assert edge.source_record_date == date(2020, 1, 2)
    assert "First observed" in edge.evidence_text


def test_resolver_requires_existing_geo_source_and_missing_dataset_fails(session: Session) -> None:
    dataset, _ = seed(session)
    dataset.source = "development_fixture"
    session.commit()
    with pytest.raises(ConflictError):
        DatasetService(session).resolve_publications(dataset.id)
    with pytest.raises(NotFoundError):
        DatasetService(session).resolve_publications(999999999)


def test_citation_foreign_keys_and_unique_identity(session: Session) -> None:
    dataset, publication = seed(session)
    DatasetService(session).resolve_publications(dataset.id)
    original = session.scalar(select(DatasetPublication))
    session.add(
        DatasetPublication(
            dataset_id=dataset.id,
            publication_id=publication.id,
            reported_pmid="123456",
            source_record_date=original.source_record_date,
            evidence_kind="structured_metadata",
            source="NCBI GEO",
            source_identifier="GSE999999",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.delete(publication)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_protected_resolution_api_and_graph_empty_and_missing(client: TestClient) -> None:
    payload = parse_geo_series(SOFT, "GSE999999").model_dump(mode="json")
    assert client.post("/api/v1/datasets/1/resolve-publications").status_code in {401, 503}
    client.app.dependency_overrides[require_admin] = lambda: None
    try:
        created = client.post("/api/v1/datasets", json=payload)
        identifier = created.json()["id"]
        response = client.post(f"/api/v1/datasets/{identifier}/resolve-publications")
        assert response.status_code == 200 and response.json()["missing_pmids"] == ["123456"]
        graph = client.get(f"/api/v1/graph/dataset/{identifier}").json()
        assert len(graph["nodes"]) == 1 and not graph["edges"]
        assert client.get("/api/v1/graph/dataset/999999").status_code == 404
        assert client.get(f"/api/v1/relationships/dataset/{identifier}").json()["total"] == 0
        assert client.post("/api/v1/datasets/0/resolve-publications").status_code == 422
    finally:
        client.app.dependency_overrides.pop(require_admin)


def test_resolution_api_bidirectional_links_and_graph(client: TestClient, session: Session) -> None:
    dataset, publication = seed(session)
    client.app.dependency_overrides[require_admin] = lambda: None
    try:
        result = client.post(f"/api/v1/datasets/{dataset.id}/resolve-publications")
        assert result.status_code == 200 and result.json()["created"] == 1
        assert (
            client.post(f"/api/v1/datasets/{dataset.id}/resolve-publications").json()["existing"]
            == 1
        )
        for kind, identifier in [("dataset", dataset.id), ("publication", publication.id)]:
            assert client.get(f"/api/v1/relationships/{kind}/{identifier}").json()["total"] == 1
            graph = client.get(f"/api/v1/graph/{kind}/{identifier}").json()
            assert len(graph["nodes"]) == 2 and len(graph["edges"]) == 1
            assert graph["edges"][0]["assertion"]["source_record_date"] == "2020-01-02"
    finally:
        client.app.dependency_overrides.pop(require_admin)
