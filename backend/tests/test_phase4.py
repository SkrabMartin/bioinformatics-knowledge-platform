from fastapi.testclient import TestClient


def create_record(client: TestClient, path: str, payload: dict[str, object]) -> dict[str, object]:
    response = client.post(path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def seed_entities(client: TestClient) -> dict[str, int]:
    organism = create_record(
        client,
        "/api/v1/organisms",
        {
            "scientific_name": "Homo sapiens",
            "taxonomy_id": "9606",
            "source": "development_fixture",
            "source_identifier": "test-organism",
        },
    )
    organism_id = int(organism["id"])
    gene = create_record(
        client,
        "/api/v1/genes",
        {
            "symbol": "DEMO1",
            "name": "Demo gene one",
            "organism_id": organism_id,
            "source": "development_fixture",
            "source_identifier": "test-gene",
        },
    )
    protein_a = create_record(
        client,
        "/api/v1/proteins",
        {
            "accession": "DEMO-P1",
            "name": "Demo protein one",
            "gene_id": gene["id"],
            "organism_id": organism_id,
            "source": "development_fixture",
            "source_identifier": "test-protein-1",
        },
    )
    protein_b = create_record(
        client,
        "/api/v1/proteins",
        {
            "accession": "DEMO-P2",
            "name": "Demo protein two",
            "organism_id": organism_id,
            "source": "development_fixture",
            "source_identifier": "test-protein-2",
        },
    )
    disease = create_record(
        client,
        "/api/v1/diseases",
        {
            "name": "Demo condition",
            "description": "A test-only condition, not a scientific record.",
            "mondo_id": "MONDO:9999999",
            "source": "development_fixture",
            "source_identifier": "test-disease",
        },
    )
    variant = create_record(
        client,
        "/api/v1/variants",
        {
            "hgvs": "DEMO:variant-1",
            "organism_id": organism_id,
            "source": "development_fixture",
            "source_identifier": "test-variant",
        },
    )
    return {
        "organism": organism_id,
        "gene": int(gene["id"]),
        "protein_a": int(protein_a["id"]),
        "protein_b": int(protein_b["id"]),
        "disease": int(disease["id"]),
        "variant": int(variant["id"]),
    }


def provenance(identifier: str) -> dict[str, str]:
    return {
        "source": "development_fixture",
        "source_identifier": identifier,
        "evidence_text": "Test-only relationship; not scientific evidence.",
    }


def test_disease_and_variant_endpoints_validate_identifiers(client: TestClient) -> None:
    ids = seed_entities(client)

    disease = client.get("/api/v1/diseases/by-mondo/MONDO:9999999")
    variants = client.get("/api/v1/variants")
    invalid_variant = client.post(
        "/api/v1/variants",
        json={
            "organism_id": ids["organism"],
            "source": "development_fixture",
            "source_identifier": "missing-identifier",
        },
    )
    duplicate_disease = client.post(
        "/api/v1/diseases",
        json={
            "name": "Demo condition",
            "source": "development_fixture",
            "source_identifier": "duplicate",
        },
    )
    clear_identifier = client.patch(f"/api/v1/variants/{ids['variant']}", json={"hgvs": None})

    assert disease.status_code == 200
    assert disease.json()["id"] == ids["disease"]
    assert variants.status_code == 200
    assert variants.json()["total"] == 1
    assert variants.json()["items"][0]["organism"]["taxonomy_id"] == "9606"
    assert invalid_variant.status_code == 422
    assert duplicate_disease.status_code == 409
    assert clear_identifier.status_code == 422


def test_typed_relationships_are_provenance_bearing_and_bidirectionally_browsable(
    client: TestClient,
) -> None:
    ids = seed_entities(client)
    gene_disease = create_record(
        client,
        "/api/v1/relationships/gene-disease",
        {"gene_id": ids["gene"], "disease_id": ids["disease"], **provenance("gd-1")},
    )
    variant_gene = create_record(
        client,
        "/api/v1/relationships/variant-gene",
        {"variant_id": ids["variant"], "gene_id": ids["gene"], **provenance("vg-1")},
    )
    variant_disease = create_record(
        client,
        "/api/v1/relationships/variant-disease",
        {"variant_id": ids["variant"], "disease_id": ids["disease"], **provenance("vd-1")},
    )
    interaction = create_record(
        client,
        "/api/v1/relationships/protein-interaction",
        {
            "protein_a_id": ids["protein_b"],
            "protein_b_id": ids["protein_a"],
            **provenance("ppi-1"),
        },
    )

    gene_edges = client.get(f"/api/v1/relationships/gene/{ids['gene']}").json()
    disease_edges = client.get(f"/api/v1/relationships/disease/{ids['disease']}").json()
    variant_edges = client.get(f"/api/v1/relationships/variant/{ids['variant']}").json()
    protein_edges = client.get(f"/api/v1/relationships/protein/{ids['protein_a']}").json()
    first_page = client.get(
        f"/api/v1/relationships/gene/{ids['gene']}", params={"page_size": 1}
    ).json()

    assert gene_disease["predicate"] == "associated_with"
    assert gene_disease["source_identifier"] == "gd-1"
    assert gene_disease["evidence_text"].startswith("Test-only")
    assert gene_disease["subject"]["href"] == "/gene/DEMO1?taxonomy_id=9606"
    assert variant_gene["predicate"] == "located_in"
    assert variant_disease["object"]["href"] == f"/disease/{ids['disease']}"
    assert interaction["subject"]["entity_id"] == min(ids["protein_a"], ids["protein_b"])
    assert {edge["relationship_type"] for edge in gene_edges["items"]} == {
        "gene_disease",
        "variant_gene",
        "gene_protein",
    }
    assert {edge["relationship_type"] for edge in disease_edges["items"]} == {
        "gene_disease",
        "variant_disease",
    }
    assert {edge["relationship_type"] for edge in variant_edges["items"]} == {
        "variant_gene",
        "variant_disease",
    }
    assert {edge["relationship_type"] for edge in protein_edges["items"]} == {
        "gene_protein",
        "protein_interaction",
    }
    assert (
        next(edge for edge in gene_edges["items"] if edge["relationship_type"] == "gene_protein")[
            "provenance_basis"
        ]
        == "protein_record"
    )
    assert first_page["total"] == 3
    assert first_page["pages"] == 3
    assert len(first_page["items"]) == 1


def test_relationship_integrity_and_duplicate_assertions(client: TestClient) -> None:
    ids = seed_entities(client)
    payload = {
        "gene_id": ids["gene"],
        "disease_id": ids["disease"],
        **provenance("gd-duplicate"),
    }
    assert client.post("/api/v1/relationships/gene-disease", json=payload).status_code == 201
    assert client.post("/api/v1/relationships/gene-disease", json=payload).status_code == 409
    assert (
        client.post(
            "/api/v1/relationships/gene-disease",
            json={**payload, "gene_id": 999999},
        ).status_code
        == 404
    )
    self_interaction = client.post(
        "/api/v1/relationships/protein-interaction",
        json={
            "protein_a_id": ids["protein_a"],
            "protein_b_id": ids["protein_a"],
            **provenance("self"),
        },
    )
    assert self_interaction.status_code == 201
    assert (
        self_interaction.json()["subject"]["entity_id"]
        == self_interaction.json()["object"]["entity_id"]
    )
    other_organism = create_record(
        client,
        "/api/v1/organisms",
        {
            "scientific_name": "Demo species two",
            "taxonomy_id": "9999999",
            "source": "development_fixture",
            "source_identifier": "test-organism-2",
        },
    )
    other_variant = create_record(
        client,
        "/api/v1/variants",
        {
            "hgvs": "DEMO:variant-2",
            "organism_id": other_organism["id"],
            "source": "development_fixture",
            "source_identifier": "test-variant-2",
        },
    )
    assert (
        client.post(
            "/api/v1/relationships/variant-gene",
            json={
                "variant_id": other_variant["id"],
                "gene_id": ids["gene"],
                **provenance("wrong-organism"),
            },
        ).status_code
        == 409
    )
    variant_link = client.post(
        "/api/v1/relationships/variant-gene",
        json={
            "variant_id": ids["variant"],
            "gene_id": ids["gene"],
            **provenance("valid-vg"),
        },
    )
    assert variant_link.status_code == 201
    assert (
        client.patch(
            f"/api/v1/variants/{ids['variant']}",
            json={"organism_id": other_organism["id"]},
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/genes/{ids['gene']}",
            json={"organism_id": other_organism["id"]},
        ).status_code
        == 409
    )
    interaction = {
        "protein_a_id": ids["protein_a"],
        "protein_b_id": ids["protein_b"],
        **provenance("interaction-duplicate"),
    }
    assert (
        client.post("/api/v1/relationships/protein-interaction", json=interaction).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/relationships/protein-interaction",
            json={
                **interaction,
                "protein_a_id": ids["protein_b"],
                "protein_b_id": ids["protein_a"],
            },
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/proteins/{ids['protein_b']}",
            json={"organism_id": other_organism["id"]},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/relationships/protein-interaction",
            json={
                "protein_a_id": ids["protein_a"],
                "protein_b_id": ids["protein_b"],
                **provenance("cross-organism"),
            },
        ).status_code
        == 201
    )
    assert client.get("/api/v1/relationships/gene/999999").status_code == 404
