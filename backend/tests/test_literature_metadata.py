"""Synthetic keyword metadata and variant assertions, isolated from public data."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.ingestion.publications import PublicationIngestionService
from app.integrations.errors import UpstreamResponseError
from app.integrations.ncbi.pubmed import parse_publication
from app.models import Organism, Publication, PublicationVariant, Variant
from app.schemas.graph import GraphLimits
from app.schemas.publication import PublicationLinkCreate
from app.schemas.search import SearchEntityType
from app.schemas.variant import VariantUpdate
from app.search import SearchService
from app.services.entities import VariantService
from app.services.errors import ConflictError, NotFoundError
from app.services.graph import GraphService
from app.services.publications import PublicationService
from app.services.relationships import RelationshipService
from tests.test_publications import XML


def keyword_xml(values: list[str]) -> str:
    nodes = "".join(f"<Keyword>{value}</Keyword>" for value in values)
    return XML.replace(
        "</MedlineCitation>", f'<KeywordList Owner="NOTNLM">{nodes}</KeywordList></MedlineCitation>'
    )


class Provider:
    xml = keyword_xml(["CytometryOnly", "žluťoučký"])

    def fetch_publication(self, identifier: str):
        return parse_publication(self.xml, identifier)


def test_xml_supplied_keywords_are_bounded_and_normalized_without_inference() -> None:
    record = parse_publication(
        keyword_xml([" CytometryOnly ", "cytometryonly", "žluťoučký", ""]), "123456"
    )
    assert record.keywords == ["CytometryOnly", "žluťoučký"]
    assert parse_publication(XML, "123456").keywords == []
    for values in [["x"] * 257, ["x" * 257]]:
        with pytest.raises(UpstreamResponseError):
            parse_publication(keyword_xml(values), "123456")


def test_keyword_ingestion_search_unicode_and_refresh(session: Session) -> None:
    provider = Provider()
    imported = PublicationIngestionService(session, provider).import_publication("123456")
    assert session.get(Publication, imported.entity_id).keywords == ["CytometryOnly", "žluťoučký"]
    service = SearchService(session)
    for query in ["CytometryOnly", "žluťoučký"]:
        result = service.search(
            query, page=1, page_size=20, entity_types=[SearchEntityType.PUBLICATION]
        )
        assert result.total == 1
        assert any(field.field == "keywords" for field in result.items[0].matched_fields)
        assert (
            PublicationService(session)
            .browse(page=1, page_size=20, query=query, sort="relevance", gene_id=None)
            .total
            == 1
        )
    assert service.search("%", page=1, page_size=20).total == 0
    assert (
        PublicationIngestionService(session, provider).import_publication("123456").action
        == "unchanged"
    )
    provider.xml = keyword_xml(["Changed source keyword"])
    assert (
        PublicationIngestionService(session, provider).import_publication("123456").action
        == "updated"
    )
    assert session.get(Publication, imported.entity_id).keywords == ["Changed source keyword"]


def seeded_variant(session: Session) -> int:
    organism = Organism(scientific_name="Synthetic organism", source="test_source")
    session.add(organism)
    session.flush()
    variant = Variant(rsid="rs999999999999", organism_id=organism.id, source="test_source")
    session.add(variant)
    session.commit()
    return variant.id


def test_variant_literature_assertions_are_source_backed_bidirectional_and_graphed(
    session: Session,
) -> None:
    publication_id = (
        PublicationIngestionService(session, Provider()).import_publication("123456").entity_id
    )
    variant_id = seeded_variant(session)
    data = PublicationLinkCreate(
        entity_id=variant_id,
        evidence_kind="curated",
        source="test_source",
        source_identifier="TEST:variant-mention",
        evidence_text="Synthetic annotation only",
    )
    result = PublicationService(session).link(publication_id, "variant", data)
    assert result.relationship_type == "publication_variant" and result.predicate == "mentions"
    assert result.object.entity_type == "variant" and result.object.href == f"/variant/{variant_id}"
    assert result.evidence_kind == "curated" and result.evidence_text == "Synthetic annotation only"
    assert (
        RelationshipService(session).list_for("variant", variant_id, page=1, page_size=20).total
        == 1
    )
    graph = GraphService(session).explore("variant", variant_id, limits=GraphLimits())
    assert (
        len(graph.edges) == 1
        and graph.edges[0].assertion.relationship_type == "publication_variant"
    )
    with pytest.raises(ConflictError):
        PublicationService(session).link(publication_id, "variant", data)
    with pytest.raises(NotFoundError):
        PublicationService(session).link(
            publication_id, "variant", data.model_copy(update={"entity_id": 999})
        )
    with pytest.raises(ConflictError):
        VariantService(session).update(variant_id, VariantUpdate(rsid="rs123"))
    assert session.scalar(select(PublicationVariant.variant_id)) == variant_id


def test_variant_literature_api_is_protected_and_validates_targets(
    client: TestClient, session: Session
) -> None:
    publication_id = (
        PublicationIngestionService(session, Provider()).import_publication("123456").entity_id
    )
    variant_id = seeded_variant(session)
    url = f"/api/v1/publications/{publication_id}/links/variant"
    data = {
        "entity_id": variant_id,
        "evidence_kind": "curated",
        "source": "test_source",
        "source_identifier": "TEST",
    }
    assert client.post(url, json=data).status_code in {401, 503}
    client.app.dependency_overrides[require_admin] = lambda: None
    try:
        assert client.post(url, json=data).status_code == 201
        assert client.post(url, json=data).status_code == 409
        assert client.get(f"/api/v1/publications/{publication_id}").json()["keywords"] == [
            "CytometryOnly",
            "žluťoučký",
        ]
    finally:
        client.app.dependency_overrides.pop(require_admin)
