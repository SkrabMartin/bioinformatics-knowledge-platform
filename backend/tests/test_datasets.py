"""Synthetic GEO metadata; never experimental data or real biological assertions."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.integrations.errors import UpstreamResponseError
from app.integrations.geo import GeoSeriesAdapter, parse_geo_series
from app.schemas.search import SearchEntityType
from app.search import SearchService
from app.services.datasets import DatasetService
from app.services.errors import ConflictError

SOFT = """^SERIES = GSE999999
!Series_geo_accession = GSE999999
!Series_status = Public on Jan 01 2020
!Series_title = Synthetic discovery study
!Series_summary = A test-only source summary.
!Series_type = Test assay
!Series_sample_organism = Synthetic organism
!Series_sample_taxid = 999999
!Series_platform_id = GPL999999
!Series_pubmed_id = 123456
!Series_last_update_date = Jan 02 2020
!Series_sample_id = GSM999991
!Series_sample_id = GSM999992
!Series_contact_email = hidden@example.test
"""


def test_geo_parser_retains_only_metadata_and_counted_samples() -> None:
    record = parse_geo_series(SOFT, "GSE999999")
    assert record.sample_count == 2 and record.taxonomy_ids == ["999999"]
    assert record.publication_pmids == ["123456"] and record.platform_accessions == ["GPL999999"]
    assert record.source_updated_date.isoformat() == "2020-01-02"
    assert "hidden@example.test" not in record.model_dump_json()
    assert (
        parse_geo_series(
            SOFT.replace("!Series_sample_id = GSM999991\n", "").replace(
                "!Series_sample_id = GSM999992\n", ""
            ),
            "GSE999999",
        ).sample_count
        is None
    )


@pytest.mark.parametrize(
    "raw",
    [
        SOFT.replace("^SERIES = GSE999999", "^SERIES = GSE123"),
        SOFT.replace("Public on Jan 01 2020", "Private"),
        SOFT + "\n^SAMPLE = GSM999991",
        SOFT + "\n!Series_sample_id = GSM999991",
        SOFT.replace("Jan 02 2020", "Unknown date"),
        SOFT.replace("GSM999992", "bad-id"),
        SOFT.replace("!Series_sample_taxid = 999999", "!Series_sample_taxid = false"),
        "<html>Provider error</html>",
    ],
)
def test_geo_parser_fails_closed_for_mismatches_private_truncated_or_invalid_metadata(raw) -> None:
    with pytest.raises(UpstreamResponseError):
        parse_geo_series(raw, "GSE999999")


def test_geo_adapter_requests_one_metadata_self_record_only() -> None:
    class Transport:
        def __init__(self):
            self.calls = []

        def get_text(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return SOFT

    transport = Transport()
    result = GeoSeriesAdapter(transport).fetch_dataset("GSE999999")
    assert result.accession == "GSE999999" and len(transport.calls) == 1
    assert transport.calls[0][1]["params"] == {
        "acc": "GSE999999",
        "targ": "self",
        "form": "text",
        "view": "brief",
    }
    with pytest.raises(ValueError):
        GeoSeriesAdapter(transport).fetch_dataset("https://example.test/data")


def test_dataset_identity_refresh_regression_and_search(session: Session) -> None:
    service = DatasetService(session)
    payload = parse_geo_series(SOFT, "GSE999999")
    record, action = service.save(payload, refresh=True)
    identifier = record.id
    assert action == "created"
    assert service.save(payload, refresh=True)[1] == "unchanged"
    assert (
        service.save(payload.model_copy(update={"title": "Changed source study"}), refresh=True)[1]
        == "updated"
    )
    with pytest.raises(ConflictError):
        service.save(payload)
    with pytest.raises(ConflictError):
        older = parse_geo_series(SOFT.replace("Jan 02 2020", "Jan 01 2020"), "GSE999999")
        service.save(older, refresh=True)
    assert service.get(identifier).title == "Changed source study"
    search = SearchService(session).search(
        "GSE999999", page=1, page_size=20, entity_types=[SearchEntityType.DATASET]
    )
    assert (
        search.total == search.counts.dataset == 1
        and search.items[0].href == f"/dataset/{identifier}"
    )
    assert (
        SearchService(session).suggestions("GSE999999", limit=2).items[0].entity_type == "dataset"
    )
    assert service.browse(1, 20, "%").total == 0


def test_dataset_api_pagination_source_validation_and_protected_writes(client: TestClient) -> None:
    assert client.get("/api/v1/datasets").json()["total"] == 0
    payload = parse_geo_series(SOFT, "GSE999999").model_dump(mode="json")
    assert client.post("/api/v1/datasets", json=payload).status_code in {401, 503}
    client.app.dependency_overrides[require_admin] = lambda: None
    try:
        created = client.post("/api/v1/datasets", json=payload)
        assert created.status_code == 201
        identifier = created.json()["id"]
        assert client.get(f"/api/v1/datasets/{identifier}").json()["sample_count"] == 2
        assert client.get("/api/v1/datasets/by-accession/GSE999999").json()["id"] == identifier
        assert client.post("/api/v1/datasets", json=payload).status_code == 409
        assert (
            client.post(
                "/api/v1/datasets", json=payload | {"source_identifier": "other"}
            ).status_code
            == 422
        )
        assert client.get("/api/v1/datasets?page_size=101").status_code == 422
        assert client.get("/api/v1/datasets/99999").status_code == 404
    finally:
        client.app.dependency_overrides.pop(require_admin)
