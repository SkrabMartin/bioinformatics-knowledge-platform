from fastapi.testclient import TestClient


def test_health_endpoint_is_live_and_returns_request_id(client: TestClient) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "bio-knowledge-platform-api"}
    assert response.headers["X-Request-ID"] == "test-request"


def test_openapi_documents_versioned_entity_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/genes" in paths
    assert "/api/v1/proteins" in paths
    assert "/api/v1/organisms" in paths
