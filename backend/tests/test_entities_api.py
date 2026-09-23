from fastapi.testclient import TestClient

PROVENANCE = {
    "source": "development_fixture",
    "source_identifier": "test-record",
    "source_url": None,
    "imported_at": None,
}


def create_organism(client: TestClient, taxonomy_id: str = "9606") -> dict[str, object]:
    response = client.post(
        "/api/v1/organisms",
        json={
            "scientific_name": "Homo sapiens",
            "common_name": "Human",
            "taxonomy_id": taxonomy_id,
            **PROVENANCE,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_gene(client: TestClient, organism_id: int, symbol: str = "TP53") -> dict[str, object]:
    response = client.post(
        "/api/v1/genes",
        json={
            "symbol": symbol,
            "name": f"{symbol} demo gene",
            "organism_id": organism_id,
            "chromosome": "17",
            "start_position": 10,
            "end_position": 20,
            "strand": "+",
            "ncbi_gene_id": f"demo-{symbol}",
            "ensembl_gene_id": None,
            **PROVENANCE,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_gene_crud_and_paginated_collection(client: TestClient) -> None:
    organism = create_organism(client)
    gene = create_gene(client, int(organism["id"]))

    list_response = client.get("/api/v1/genes?page=1&page_size=1")
    detail_response = client.get(f"/api/v1/genes/{gene['id']}")
    update_response = client.patch(
        f"/api/v1/genes/{gene['id']}", json={"description": "Updated demo description"}
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["pages"] == 1
    assert list_response.json()["items"][0]["organism"]["taxonomy_id"] == "9606"
    assert detail_response.status_code == 200
    assert detail_response.json()["symbol"] == "TP53"
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Updated demo description"


def test_protein_links_gene_and_organism(client: TestClient) -> None:
    organism = create_organism(client)
    gene = create_gene(client, int(organism["id"]))

    response = client.post(
        "/api/v1/proteins",
        json={
            "accession": "DEMO-P04637",
            "name": "Demo protein",
            "gene_id": gene["id"],
            "organism_id": organism["id"],
            "function": "Test-only function text.",
            "sequence_length": 393,
            **PROVENANCE,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["gene"]["symbol"] == "TP53"
    assert payload["organism"]["scientific_name"] == "Homo sapiens"

    gene_detail = client.get("/api/v1/genes/by-symbol/tp53?taxonomy_id=9606")
    protein_detail = client.get("/api/v1/proteins/by-accession/demo-p04637")

    assert gene_detail.status_code == 200
    assert gene_detail.json()["proteins"][0]["accession"] == "DEMO-P04637"
    assert protein_detail.status_code == 200
    assert protein_detail.json()["gene"]["symbol"] == "TP53"


def test_duplicate_stable_identifier_returns_conflict(client: TestClient) -> None:
    create_organism(client)

    response = client.post(
        "/api/v1/organisms",
        json={
            "scientific_name": "Duplicate demo",
            "taxonomy_id": "9606",
            **PROVENANCE,
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert response.json()["error"]["request_id"]


def test_not_found_and_validation_use_error_envelope(client: TestClient) -> None:
    missing = client.get("/api/v1/genes/999")
    invalid = client.get("/api/v1/genes?page=0")

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "gene_not_found"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert invalid.json()["error"]["details"][0]["field"] == "query.page"


def test_partial_updates_validate_required_fields_and_merged_coordinates(
    client: TestClient,
) -> None:
    organism = create_organism(client)
    gene = create_gene(client, int(organism["id"]))

    null_required = client.patch(f"/api/v1/genes/{gene['id']}", json={"symbol": None})
    invalid_coordinates = client.patch(f"/api/v1/genes/{gene['id']}", json={"start_position": 30})

    assert null_required.status_code == 422
    assert null_required.json()["error"]["code"] == "validation_error"
    assert invalid_coordinates.status_code == 422
    assert "end_position" in invalid_coordinates.json()["error"]["message"]


def test_rejects_cross_organism_protein_gene_link(client: TestClient) -> None:
    human = create_organism(client, "9606")
    mouse = create_organism(client, "10090")
    gene = create_gene(client, int(human["id"]))

    response = client.post(
        "/api/v1/proteins",
        json={
            "accession": "DEMO-CROSS-LINK",
            "name": "Invalid demo protein",
            "gene_id": gene["id"],
            "organism_id": mouse["id"],
            **PROVENANCE,
        },
    )

    assert response.status_code == 409
    assert "same organism" in response.json()["error"]["message"]
