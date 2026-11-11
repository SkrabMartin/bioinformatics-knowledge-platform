"""Synthetic phenotype terms and assertions; no biological facts are imported."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.models import Disease
from app.schemas.search import SearchEntityType
from app.search import SearchService


def term(number: int = 1) -> dict:
    return {
        "hpo_id": f"HP:{number:07}",
        "name": f"Synthetic phenotype {number}",
        "description": "A test fixture, not a biological assertion.",
        "source": "test_source",
        "source_identifier": f"HP:{number:07}",
        "source_release": "TEST-1",
        "source_url": "https://example.test/term",
        "imported_at": "2026-11-11T00:00:00Z",
    }


def assertion(phenotype_id: int, qualifier: str = "present") -> dict:
    return {k: v for k, v in term().items() if k not in {"hpo_id", "name", "description"}} | {
        "phenotype_id": phenotype_id,
        "qualifier": qualifier,
        "evidence_kind": "structured_metadata",
        "evidence_code": "TEST",
        "reference": "TEST:reference",
        "source_identifier": "TEST:assertion",
    }


@pytest.fixture
def admin(client: TestClient):
    client.app.dependency_overrides[require_admin] = lambda: None
    yield client
    client.app.dependency_overrides.pop(require_admin)


def seed_disease(session: Session) -> int:
    record = Disease(name="Synthetic disease", source="test_source")
    session.add(record)
    session.commit()
    return record.id


def test_writes_fail_closed_without_configured_admin(client: TestClient) -> None:
    assert client.post("/api/v1/phenotypes", json=term()).status_code in {401, 503}
    assert client.post("/api/v1/diseases/1/phenotypes", json=assertion(1)).status_code in {401, 503}


def test_create_browse_filter_detail_and_duplicate_rollback(admin: TestClient) -> None:
    first = admin.post("/api/v1/phenotypes", json=term())
    assert first.status_code == 201
    identifier = first.json()["id"]
    assert admin.get(f"/api/v1/phenotypes/{identifier}").json()["hpo_id"] == "HP:0000001"
    assert admin.post("/api/v1/phenotypes", json=term()).status_code == 409
    assert admin.post("/api/v1/phenotypes", json=term(2)).status_code == 201
    assert admin.get("/api/v1/phenotypes", params={"q": "HP:0000002"}).json()["total"] == 1
    assert admin.get("/api/v1/phenotypes", params={"q": "%"}).json()["total"] == 0
    result = admin.get("/api/v1/phenotypes?page_size=1&page=2").json()
    assert result["total"] == 2 and result["pages"] == 2
    assert result["items"][0]["hpo_id"] == "HP:0000002"


@pytest.mark.parametrize(
    "field,value",
    [
        ("hpo_id", "GO:0000001"),
        ("hpo_id", "HP:123"),
        ("name", " "),
        ("source_identifier", " "),
        ("source_release", ""),
        ("source_url", "bad"),
        ("imported_at", "2026-11-11T00:00:00"),
    ],
)
def test_invalid_or_incomplete_term_is_rejected(admin: TestClient, field, value) -> None:
    assert admin.post("/api/v1/phenotypes", json=term() | {field: value}).status_code == 422


def test_positive_and_excluded_assertions_remain_distinct_and_paginated(
    admin: TestClient, session: Session
) -> None:
    disease_id = seed_disease(session)
    phenotype_id = admin.post("/api/v1/phenotypes", json=term()).json()["id"]
    url = f"/api/v1/diseases/{disease_id}/phenotypes"
    assert admin.post(url, json=assertion(phenotype_id)).status_code == 201
    assert admin.post(url, json=assertion(phenotype_id, "excluded")).status_code == 201
    assert admin.post(url, json=assertion(phenotype_id)).status_code == 409
    result = admin.get(url + "?page_size=1&page=2").json()
    assert result["total"] == 2 and result["items"][0]["qualifier"] == "excluded"
    record = result["items"][0]
    assert record["reference"] == "TEST:reference" and record["phenotype"]["hpo_id"] == "HP:0000001"
    inverse = admin.get(f"/api/v1/phenotypes/{phenotype_id}/diseases").json()
    assert inverse["total"] == 2 and inverse["items"][0]["disease"]["id"] == disease_id
    payload = assertion(phenotype_id)
    payload.pop("qualifier")
    assert admin.post(url, json=payload).status_code == 422
    assert admin.post(url, json=assertion(phenotype_id) | {"reference": " "}).status_code == 422
    assert (
        admin.post(url, json=assertion(phenotype_id) | {"qualifier": "inferred"}).status_code == 422
    )


def test_missing_parents_and_page_bounds(admin: TestClient) -> None:
    phenotype_id = admin.post("/api/v1/phenotypes", json=term()).json()["id"]
    assert (
        admin.post("/api/v1/diseases/999/phenotypes", json=assertion(phenotype_id)).status_code
        == 404
    )
    assert admin.get("/api/v1/phenotypes/999/diseases").status_code == 404
    assert admin.get("/api/v1/diseases/999/phenotypes").status_code == 404
    assert admin.get("/api/v1/phenotypes?page_size=101").status_code == 422
    assert admin.get("/api/v1/phenotypes/0").status_code == 422


def test_search_includes_phenotype_identity_without_disease_inference(
    admin: TestClient, session: Session
) -> None:
    created = admin.post("/api/v1/phenotypes", json=term()).json()
    result = SearchService(session).search(
        "HP:0000001", page=1, page_size=20, entity_types=[SearchEntityType.PHENOTYPE]
    )
    assert result.total == result.counts.phenotype == 1
    assert result.items[0].href == f"/phenotype/{created['id']}"
    assert result.items[0].score >= 1300 and result.items[0].source == "test_source"
    assert result.counts.disease == 0
