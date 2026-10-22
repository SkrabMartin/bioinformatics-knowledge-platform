"""Synthetic literature contracts. These records are not scientific evidence."""

import gzip
from datetime import UTC, datetime
from unittest.mock import Mock

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.publications import NormalizedPublication, PublicationIngestionService
from app.ingestion.services import IngestionPersistenceError
from app.integrations.errors import (
    IntegrationConfigurationError,
    UpstreamNotFoundError,
    UpstreamResponseError,
)
from app.integrations.http import RetryingJsonClient
from app.integrations.ncbi.pubmed import PubMedAdapter, parse_publication
from app.models import Disease, Gene, Organism, Protein, Publication, PublicationGene
from app.schemas.publication import PublicationFields
from app.schemas.search import SearchEntityType
from app.search import SearchService

XML = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123456</PMID>
<Article><ArticleTitle>Demo <i>literature</i> record</ArticleTitle><Journal>
<Title>Test-only journal</Title><JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue>
</Journal><AuthorList><Author><ForeName>Demo</ForeName><LastName>Author</LastName></Author>
<Author><CollectiveName>Test Consortium</CollectiveName></Author></AuthorList>
<Abstract><AbstractText Label="RESULTS">Synthetic example, not evidence.</AbstractText></Abstract>
</Article></MedlineCitation><PubmedData><ArticleIdList>
<ArticleId IdType="doi">10.1234/DEMO</ArticleId></ArticleIdList></PubmedData>
</PubmedArticle></PubmedArticleSet>"""


def publication(**values: object) -> NormalizedPublication:
    return parse_publication(XML, "123456").model_copy(update=values)


def seed_gene(session: Session) -> Gene:
    organism = Organism(
        scientific_name="Demo organism", taxonomy_id="999999", source="development_fixture"
    )
    session.add(organism)
    session.flush()
    gene = Gene(
        symbol="DEMO",
        name="Test-only gene",
        organism_id=organism.id,
        ncbi_gene_id="99999",
        source="development_fixture",
    )
    session.add(gene)
    session.commit()
    return gene


def import_record(session: Session, record: NormalizedPublication | None = None):
    provider = Mock()
    provider.fetch_publication.return_value = record or publication()
    return PublicationIngestionService(session, provider).import_publication("123456")


def test_pubmed_parser_preserves_partial_date_authors_and_plain_text() -> None:
    record = parse_publication(XML, "123456")
    assert record.publication_date == "2020"
    assert record.publication_date_text == "2020"
    assert record.title == "Demo literature record"
    assert record.authors == ["Demo Author", "Test Consortium"]
    assert record.abstract == "RESULTS: Synthetic example, not evidence."
    assert record.doi == "10.1234/demo"
    assert record.linked_ncbi_gene_ids == []
    month = XML.replace("<Year>2020</Year>", "<Year>2020</Year><Month>Feb</Month>")
    assert parse_publication(month, "123456").publication_date == "2020-02"
    medline = XML.replace("<Year>2020</Year>", "<MedlineDate>2020 Winter</MedlineDate>")
    assert parse_publication(medline, "123456").publication_date == "2020"
    missing = XML.replace("<Year>2020</Year>", "")
    assert parse_publication(missing, "123456").publication_date is None


@pytest.mark.parametrize(
    "xml",
    [
        "<bad",
        XML.replace("<PMID>123456", "<PMID>999"),
        '<!DOCTYPE x [<!ENTITY bomb "expansion">]><PubmedArticleSet>&bomb;</PubmedArticleSet>',
    ],
)
def test_pubmed_parser_rejects_malformed_mismatched_and_unsafe_xml(xml: str) -> None:
    with pytest.raises(UpstreamResponseError):
        parse_publication(xml, "123456")


def test_missing_pubmed_record_and_invalid_metadata_are_safe_failures() -> None:
    with pytest.raises(UpstreamNotFoundError):
        parse_publication("<PubmedArticleSet/>", "123456")
    with pytest.raises(UpstreamResponseError):
        parse_publication(
            XML.replace("<Year>2020</Year>", "<Year>2020</Year><Month>02</Month><Day>31</Day>"),
            "123456",
        )
    with pytest.raises(ValidationError):
        PublicationFields(title="Demo", source="development_fixture")


def test_transport_retries_decompresses_and_bounds_payloads() -> None:
    attempts = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        attempts.append(request)
        if len(attempts) == 1:
            return httpx2.Response(429, headers={"Retry-After": "0"})
        return httpx2.Response(
            200, headers={"Content-Encoding": "gzip"}, content=gzip.compress(XML.encode())
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        transport = RetryingJsonClient(client, provider="test", max_attempts=2, backoff_seconds=0)
        assert "PubmedArticleSet" in transport.get_text(
            "https://example.test", not_found_message="Missing"
        )
    with (
        httpx2.Client(
            transport=httpx2.MockTransport(
                lambda request: httpx2.Response(200, content=b"x" * 2_000_001)
            )
        ) as client,
        pytest.raises(UpstreamResponseError, match="single-record limit"),
    ):
        RetryingJsonClient(client, provider="test", max_attempts=1, backoff_seconds=0).get_text(
            "https://example.test", not_found_message="Missing"
        )


def test_pubmed_adapter_only_accepts_structured_links_and_requires_contact() -> None:
    http = Mock()
    http.get_text.return_value = XML
    http.get_json.return_value = {
        "linksets": [
            {"ids": ["123456"], "linksetdbs": [{"linkname": "pubmed_gene", "links": [99999]}]}
        ]
    }
    with pytest.raises(IntegrationConfigurationError):
        PubMedAdapter(http, base_url="https://example.test", tool="test", email=None)
    provider = PubMedAdapter(
        http,
        base_url="https://example.test",
        tool="test",
        email="owner@example.test",
        sleeper=lambda _: None,
    )
    assert provider.fetch_publication("123456").linked_ncbi_gene_ids == ["99999"]
    http.get_json.return_value = {"error": "bad response"}
    with pytest.raises(UpstreamResponseError):
        provider.fetch_publication("123456")


def test_import_is_idempotent_and_links_only_existing_identified_genes(session: Session) -> None:
    gene = seed_gene(session)
    record = publication(linked_ncbi_gene_ids=["99999", "11111"])
    first = import_record(session, record)
    second = import_record(session, record)
    assert first.action == "created"
    assert first.gene_links_created == 1
    assert second.action == "unchanged"
    assert second.gene_links_created == 0
    assert first.entity_id == second.entity_id
    assert session.scalar(select(func.count()).select_from(Publication)) == 1
    assert session.scalar(select(func.count()).select_from(Gene)) == 1
    edge = session.scalar(select(PublicationGene))
    assert edge.gene_id == gene.id
    assert edge.evidence_kind == "structured_metadata"
    updated = import_record(
        session,
        record.model_copy(update={"title": "Updated demo title", "imported_at": datetime.now(UTC)}),
    )
    assert updated.action == "updated"
    assert session.get(Publication, first.entity_id).title == "Updated demo title"


def test_import_does_not_infer_gene_links_from_text(session: Session) -> None:
    seed_gene(session)
    result = import_record(session, publication(title="DEMO gene and 99999 mentioned in test text"))
    assert result.gene_links_created == 0


def test_conflicting_pmid_and_doi_roll_back_without_merging(session: Session) -> None:
    first = import_record(session)
    with pytest.raises(IngestionPersistenceError):
        import_record(session, publication(pubmed_id="654321"))
    assert session.scalar(select(func.count()).select_from(Publication)) == 1
    assert session.get(Publication, first.entity_id).pubmed_id == "123456"
    import_record(session, publication(pubmed_id="654321", doi="10.1234/other"))
    with pytest.raises(IngestionPersistenceError):
        import_record(session, publication(doi="10.1234/other"))
    with pytest.raises(IngestionPersistenceError):
        import_record(session, publication(doi="10.1234/new-conflict"))


def test_publication_api_search_sort_pagination_and_gene_relations(
    client: TestClient, session: Session
) -> None:
    # API fixtures share the Engine but use independent Sessions.
    gene = seed_gene(session)
    first = import_record(session, publication(linked_ncbi_gene_ids=["99999"]))
    import_record(
        session,
        publication(
            pubmed_id="654321",
            doi="10.1234/other",
            publication_date="2022-03",
            title="Another synthetic literature record",
        ),
    )
    listing = client.get("/api/v1/publications", params={"page_size": 1, "sort": "oldest"})
    assert listing.json()["total"] == 2
    assert listing.json()["items"][0]["id"] == first.entity_id
    assert (
        client.get("/api/v1/publications", params={"sort": "newest"}).json()["items"][0][
            "pubmed_id"
        ]
        == "654321"
    )
    assert client.get("/api/v1/publications", params={"gene_id": gene.id}).json()["total"] == 1
    assert (
        client.get(
            "/api/v1/publications", params={"q": "10.1234/demo", "sort": "relevance"}
        ).json()["items"][0]["id"]
        == first.entity_id
    )
    assert client.get("/api/v1/publications", params={"q": "%"}).json()["total"] == 0
    assert client.get("/api/v1/publications", params={"q": "   "}).status_code == 422
    assert client.get("/api/v1/publications", params={"page_size": 101}).status_code == 422
    assert client.get("/api/v1/publications", params={"gene_id": 999999}).status_code == 404
    detail = client.get(f"/api/v1/publications/{first.entity_id}").json()
    assert detail["publication_date"] == "2020"
    assert detail["source"] == "NCBI PubMed"
    edges = client.get(f"/api/v1/relationships/gene/{gene.id}").json()["items"]
    assert edges[0]["subject"]["href"] == f"/publication/{first.entity_id}"
    assert edges[0]["evidence_kind"] == "structured_metadata"
    assert client.get(f"/api/v1/relationships/publication/{first.entity_id}").json()["total"] == 1
    search = client.get("/api/v1/search", params={"q": "123456", "type": "publication"}).json()
    assert search["counts"]["publication"] == 1
    assert search["items"][0]["score"] >= 1300
    assert search["items"][0]["href"] == f"/publication/{first.entity_id}"


def test_new_writes_fail_closed_and_require_admin_token(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    gene = seed_gene(session)
    result = import_record(session)
    route = f"/api/v1/publications/{result.entity_id}/links/gene"
    payload = {
        "entity_id": gene.id,
        "source": "development_fixture",
        "source_identifier": "demo-assertion",
        "evidence_kind": "curated",
    }
    settings = Settings(_env_file=None, admin_api_token=None)
    monkeypatch.setattr("app.core.security.get_settings", lambda: settings)
    assert client.post(route, json=payload).status_code == 503
    settings.admin_api_token = SecretStr("test-only-token")
    assert client.post(route, json=payload).status_code == 401
    headers = {"Authorization": "Bearer test-only-token"}
    created = client.post(route, json=payload, headers=headers)
    assert created.status_code == 201, created.text
    assert created.json()["evidence_kind"] == "curated"
    assert client.post(route, json=payload, headers=headers).status_code == 409
    assert (
        client.post(
            route, json={**payload, "evidence_kind": "automatically_extracted"}, headers=headers
        ).status_code
        == 422
    )


def test_postgresql_publication_document_matches_index(session: Session) -> None:
    service = SearchService(session)
    service.is_postgresql = True
    sql = str(
        service._statements("demo", ["demo"])[SearchEntityType.PUBLICATION].compile(
            dialect=postgresql.dialect()
        )
    )
    assert (
        "to_tsvector('simple'::regconfig, coalesce(publications.title, '') || ' ' || "
        "coalesce(publications.abstract, '') || ' ' || coalesce(publications.journal, ''))"
    ) in sql


@pytest.mark.parametrize(
    "entity_type,predicate", [("protein", "discusses"), ("disease", "studies")]
)
def test_curated_protein_and_disease_literature_links(
    client: TestClient,
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
    entity_type: str,
    predicate: str,
) -> None:
    gene = seed_gene(session)
    target = (
        Protein(
            accession="DEMO-LIT",
            name="Test-only protein",
            organism_id=gene.organism_id,
            source="development_fixture",
        )
        if entity_type == "protein"
        else Disease(name="Test-only condition", source="development_fixture")
    )
    session.add(target)
    session.commit()
    result = import_record(session)
    monkeypatch.setattr(
        "app.core.security.get_settings",
        lambda: Settings(_env_file=None, admin_api_token=SecretStr("test-only-token")),
    )
    created = client.post(
        f"/api/v1/publications/{result.entity_id}/links/{entity_type}",
        headers={"Authorization": "Bearer test-only-token"},
        json={
            "entity_id": target.id,
            "source": "development_fixture",
            "source_identifier": "demo-literature-link",
            "evidence_kind": "curated",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["predicate"] == predicate
    edges = client.get(f"/api/v1/relationships/{entity_type}/{target.id}").json()
    assert edges["total"] == 1
    assert edges["items"][0]["subject"]["entity_type"] == "publication"
