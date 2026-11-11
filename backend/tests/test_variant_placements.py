"""Synthetic representations only; not assertions about real genomes or alleles."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.models import Organism, Variant


def placement() -> dict:
    return {
        "assembly_name": "TEST-ASSEMBLY",
        "assembly_accession": "GCA_000000001.1",
        "sequence_accession": "TESTSEQ.1",
        "sequence_region": "TEST",
        "taxonomy_id": "999999",
        "coordinate_system": "one_based_closed",
        "strand": "+",
        "start_position": 10,
        "end_position": 11,
        "reference_allele": "AC",
        "alternate_allele": "A",
        "source": "test_source",
        "source_identifier": "TEST:placement",
        "source_release": "TEST-1",
        "source_url": "https://example.test/placement",
        "imported_at": "2026-11-11T00:00:00Z",
    }


def seed(session: Session) -> tuple[int, int]:
    organism = Organism(
        scientific_name="Synthetic variant organism", taxonomy_id="999999", source="test_source"
    )
    session.add(organism)
    session.flush()
    variant = Variant(rsid="rs999999999999", organism_id=organism.id, source="test_source")
    session.add(variant)
    session.commit()
    return variant.id, organism.id


@pytest.fixture
def admin(client: TestClient):
    client.app.dependency_overrides[require_admin] = lambda: None
    yield client
    client.app.dependency_overrides.pop(require_admin)


def test_write_is_fail_closed_and_missing_parent_is_not_fabricated(client: TestClient) -> None:
    assert client.post("/api/v1/variants/999/placements", json=placement()).status_code in {
        401,
        503,
    }
    assert client.get("/api/v1/variants/999/placements").status_code == 404


def test_creation_pagination_duplicate_rollback_and_source_versions(
    admin: TestClient, session: Session
) -> None:
    variant_id, _ = seed(session)
    url = f"/api/v1/variants/{variant_id}/placements"
    assert admin.get(url).json()["total"] == 0
    first = admin.post(url, json=placement() | {"reference_allele": "ac", "alternate_allele": "a"})
    assert first.status_code == 201 and first.json()["reference_allele"] == "AC"
    assert admin.post(url, json=placement()).status_code == 409
    assert admin.post(url, json=placement() | {"source_release": "TEST-2"}).status_code == 201
    assert (
        admin.post(url, json=placement() | {"assembly_name": "TEST-OTHER-ASSEMBLY"}).status_code
        == 201
    )
    page = admin.get(url + "?page_size=1&page=2").json()
    assert page["total"] == 3 and page["pages"] == 3
    assert page["items"][0]["source_release"] == "TEST-2"
    assert page["items"][0]["coordinate_system"] == "one_based_closed"
    assert admin.get(url + "?page_size=101").status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("start_position", 0),
        ("start_position", True),
        ("start_position", "10"),
        ("end_position", 10),
        ("coordinate_system", "zero_based_half_open"),
        ("strand", "-"),
        ("reference_allele", ""),
        ("alternate_allele", "<DEL>"),
        ("alternate_allele", "A,C"),
        ("alternate_allele", "AC"),
        ("alternate_allele", "A" * 1001),
        ("sequence_accession", "chr1"),
        ("assembly_name", " "),
        ("assembly_accession", "GCF_123"),
        ("source_identifier", " "),
        ("imported_at", "2026-11-11T00:00:00"),
    ],
)
def test_invalid_representations_are_rejected(
    admin: TestClient, session: Session, field, value
) -> None:
    variant_id, _ = seed(session)
    assert (
        admin.post(
            f"/api/v1/variants/{variant_id}/placements", json=placement() | {field: value}
        ).status_code
        == 422
    )


def test_taxonomy_must_match_and_missing_parent_is_404(admin: TestClient, session: Session) -> None:
    variant_id, _ = seed(session)
    url = f"/api/v1/variants/{variant_id}/placements"
    assert admin.post(url, json=placement() | {"taxonomy_id": "123"}).status_code == 409
    assert admin.get(url).json()["total"] == 0
    assert admin.post("/api/v1/variants/999/placements", json=placement()).status_code == 404


def test_parent_identity_and_taxonomy_are_protected_after_placement(
    admin: TestClient, session: Session
) -> None:
    variant_id, organism_id = seed(session)
    assert (
        admin.post(f"/api/v1/variants/{variant_id}/placements", json=placement()).status_code == 201
    )
    assert admin.patch(f"/api/v1/variants/{variant_id}", json={"rsid": "rs123"}).status_code == 409
    assert (
        admin.patch(f"/api/v1/variants/{variant_id}", json={"hgvs": "TEST:g.1A>C"}).status_code
        == 409
    )
    assert (
        admin.patch(f"/api/v1/organisms/{organism_id}", json={"taxonomy_id": "123"}).status_code
        == 409
    )
    assert (
        admin.patch(
            f"/api/v1/variants/{variant_id}", json={"description": "Test-only description"}
        ).status_code
        == 200
    )
    assert admin.get(f"/api/v1/variants/{variant_id}").json()["rsid"] == "rs999999999999"
