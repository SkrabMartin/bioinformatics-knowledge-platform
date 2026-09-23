from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.models import Gene, Organism, Protein
from app.schemas.search import SearchEntityType
from app.search import SearchService


def seed_search_records(session: Session) -> None:
    human = Organism(
        scientific_name="Homo sapiens",
        common_name="Human",
        taxonomy_id="9606",
        source="NCBI Taxonomy",
        source_identifier="9606",
        source_url="https://example.test/taxonomy/9606",
    )
    session.add(human)
    session.flush()
    tp53 = Gene(
        symbol="TP53",
        name="tumor protein p53",
        description="A transcription factor involved in cellular stress responses.",
        organism_id=human.id,
        chromosome="17",
        ncbi_gene_id="7157",
        ensembl_gene_id="ENSG00000141510",
        source="NCBI Gene",
        source_identifier="7157",
        source_url="https://example.test/gene/7157",
    )
    brca1 = Gene(
        symbol="BRCA1",
        name="BRCA1 DNA repair associated",
        description="A DNA repair gene used to verify partial search and pagination.",
        organism_id=human.id,
        chromosome="17",
        ncbi_gene_id="672",
        ensembl_gene_id="ENSG00000012048",
        source="NCBI Gene",
        source_identifier="672",
        source_url="https://example.test/gene/672",
    )
    session.add_all([tp53, brca1])
    session.flush()
    session.add_all(
        [
            Protein(
                accession="P04637",
                name="Cellular tumor antigen p53",
                gene_id=tp53.id,
                organism_id=human.id,
                function="Functions as a tumor suppressor transcription factor.",
                sequence_length=393,
                source="UniProt",
                source_identifier="P04637",
                source_url="https://example.test/protein/P04637",
            ),
            Protein(
                accession="P38398",
                name="Breast cancer type 1 susceptibility protein",
                gene_id=brca1.id,
                organism_id=human.id,
                function="Participates in DNA repair.",
                sequence_length=1863,
                source="UniProt",
                source_identifier="P38398",
                source_url="https://example.test/protein/P38398",
            ),
        ]
    )
    session.commit()


def seed_search_api(client: TestClient) -> None:
    organism = client.post(
        "/api/v1/organisms",
        json={
            "scientific_name": "Homo sapiens",
            "common_name": "Human",
            "taxonomy_id": "9606",
            "source": "NCBI Taxonomy",
            "source_identifier": "9606",
            "source_url": "https://example.test/taxonomy/9606",
        },
    ).json()
    gene = client.post(
        "/api/v1/genes",
        json={
            "symbol": "TP53",
            "name": "tumor protein p53",
            "description": "A tumor suppressor transcription factor.",
            "organism_id": organism["id"],
            "ncbi_gene_id": "7157",
            "ensembl_gene_id": "ENSG00000141510",
            "source": "NCBI Gene",
            "source_identifier": "7157",
            "source_url": "https://example.test/gene/7157",
        },
    ).json()
    response = client.post(
        "/api/v1/proteins",
        json={
            "accession": "P04637",
            "name": "Cellular tumor antigen p53",
            "gene_id": gene["id"],
            "organism_id": organism["id"],
            "function": "Functions as a tumor suppressor.",
            "sequence_length": 393,
            "source": "UniProt",
            "source_identifier": "P04637",
            "source_url": "https://example.test/protein/P04637",
        },
    )
    assert response.status_code == 201


def test_exact_identifiers_rank_above_related_matches(session: Session) -> None:
    seed_search_records(session)
    service = SearchService(session)

    accession = service.search("P04637", page=1, page_size=20)
    gene_symbol = service.search("TP53", page=1, page_size=20)
    gene_identifier = service.search("ENSG00000141510", page=1, page_size=20)

    assert accession.items[0].entity_type is SearchEntityType.PROTEIN
    assert accession.items[0].primary_label == "P04637"
    assert accession.items[0].score == 1300
    assert gene_symbol.items[0].entity_type is SearchEntityType.GENE
    assert gene_symbol.items[0].primary_label == "TP53"
    assert gene_symbol.items[0].score > gene_symbol.items[1].score
    assert gene_symbol.items[0].href == "/gene/TP53?taxonomy_id=9606"
    assert gene_identifier.items[0].primary_label == "TP53"
    assert gene_identifier.items[0].matched_fields[0].field == "ensembl_gene_id"


def test_partial_search_counts_filters_and_paginates_in_database(session: Session) -> None:
    seed_search_records(session)
    service = SearchService(session)

    first_page = service.search("tumor", page=1, page_size=1)
    proteins_only = service.search(
        "tumor", page=1, page_size=20, entity_types=[SearchEntityType.PROTEIN]
    )

    assert first_page.total == 2
    assert first_page.pages == 2
    assert len(first_page.items) == 1
    assert first_page.counts.gene == 1
    assert first_page.counts.protein == 1
    assert first_page.counts.organism == 0
    assert proteins_only.total == 1
    assert proteins_only.counts.total == 2
    assert proteins_only.items[0].entity_type is SearchEntityType.PROTEIN
    assert any(
        field.field in {"name", "function"} for field in proteins_only.items[0].matched_fields
    )


def test_provider_record_precedes_demo_fixture_when_scores_tie(session: Session) -> None:
    seed_search_records(session)
    tp53 = session.query(Gene).filter_by(symbol="TP53").one()
    session.add(
        Protein(
            accession="DEMO-P04637",
            name="Example fixture protein",
            gene_id=tp53.id,
            organism_id=tp53.organism_id,
            source="development_fixture",
            source_identifier="demo-protein-TP53",
        )
    )
    session.commit()

    response = SearchService(session).search("TP", page=1, page_size=10)
    proteins = [item for item in response.items if item.entity_type is SearchEntityType.PROTEIN]
    assert [item.primary_label for item in proteins] == ["P04637", "DEMO-P04637"]


def test_search_api_alias_suggestions_and_validation(client: TestClient) -> None:
    seed_search_api(client)

    canonical = client.get("/api/v1/search", params={"q": "TP53"})
    compatibility = client.get("/api/search", params={"q": "P04637"})
    suggestions = client.get("/api/v1/search/suggestions", params={"q": "TP"})
    filtered = client.get("/api/v1/search", params=[("q", "TP53"), ("type", "protein")])
    whitespace = client.get("/api/v1/search", params={"q": "   "})

    assert canonical.status_code == 200
    assert canonical.json()["items"][0]["primary_label"] == "TP53"
    assert compatibility.status_code == 200
    assert compatibility.json()["items"][0]["primary_label"] == "P04637"
    assert suggestions.status_code == 200
    assert suggestions.json()["items"][0]["value"] == "TP53"
    assert filtered.status_code == 200
    assert {item["entity_type"] for item in filtered.json()["items"]} == {"protein"}
    assert whitespace.status_code == 422
    assert whitespace.json()["error"]["code"] == "validation_error"


def test_postgresql_search_document_matches_index_expression(session: Session) -> None:
    service = SearchService(session)
    service.is_postgresql = True

    gene_sql = str(service._gene_statement("TP53", ["tp53"]).compile(dialect=postgresql.dialect()))
    protein_sql = str(
        service._protein_statement("P04637", ["p04637"]).compile(dialect=postgresql.dialect())
    )
    organism_sql = str(
        service._organism_statement("Homo", ["homo"]).compile(dialect=postgresql.dialect())
    )

    assert (
        "to_tsvector('simple'::regconfig, coalesce(genes.symbol, '') || ' ' || "
        "coalesce(genes.name, '') || ' ' || coalesce(genes.description, '') || ' ' || "
        "coalesce(genes.ncbi_gene_id, '') || ' ' || coalesce(genes.ensembl_gene_id, ''))"
    ) in gene_sql
    assert (
        "to_tsvector('simple'::regconfig, coalesce(proteins.accession, '') || ' ' || "
        "coalesce(proteins.name, '') || ' ' || coalesce(proteins.function, ''))"
    ) in protein_sql
    assert (
        "to_tsvector('simple'::regconfig, coalesce(organisms.scientific_name, '') || ' ' || "
        "coalesce(organisms.common_name, '') || ' ' || coalesce(organisms.taxonomy_id, ''))"
    ) in organism_sql


def test_like_wildcards_are_not_treated_as_match_all(session: Session) -> None:
    seed_search_records(session)
    service = SearchService(session)

    assert service.search("%", page=1, page_size=20).total == 0
    assert service.search("_", page=1, page_size=20).total == 0
