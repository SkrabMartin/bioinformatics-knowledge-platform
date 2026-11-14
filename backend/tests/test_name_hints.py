import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.search.names import name_hints, normalize_name_query
from app.services.errors import ApplicationError, InvalidInputError


@pytest.mark.parametrize(
    "query", ["TP53", "BRCA", "GSE10072", "rs123", "ENSG00001", "abc", "%%%%", "   ", "a" * 121]
)
def test_name_hints_reject_identifiers_wildcards_and_unbounded_input(query):
    with pytest.raises(InvalidInputError):
        normalize_name_query(query)


def test_name_query_normalizes_unicode_and_spaces():
    assert normalize_name_query("  Homo   sapines ") == "Homo sapines"
    assert normalize_name_query("cafe\u0301 protein") == "café protein"


def test_sqlite_does_not_invent_an_approximation(session: Session):
    with pytest.raises(ApplicationError) as error:
        name_hints(session, "Homo sapines")
    assert error.value.code == "name_hints_unavailable" and error.value.status_code == 503


def test_name_hint_api_limits_and_explicit_unavailability(client: TestClient):
    assert client.get("/api/v1/search/name-suggestions?q=TP53").status_code == 422
    assert client.get("/api/v1/search/name-suggestions?q=Homo%20sapines&limit=9").status_code == 422
    assert (
        client.get("/api/v1/search/name-suggestions?q=Homo%20sapines&type=variant").status_code
        == 422
    )
    response = client.get("/api/v1/search/name-suggestions?q=Homo%20sapines")
    assert (
        response.status_code == 503 and response.json()["error"]["code"] == "name_hints_unavailable"
    )
