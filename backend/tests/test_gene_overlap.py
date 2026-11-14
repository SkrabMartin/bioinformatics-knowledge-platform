import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Gene, GeneExternalIdentifier, Organism
from app.services.errors import InvalidInputError
from app.services.gene_overlap import gene_overlap, normalize_inputs


def seed(session):
    first = Organism(
        scientific_name="Synthetic first", taxonomy_id="999991", source="development_fixture"
    )
    second = Organism(
        scientific_name="Synthetic second", taxonomy_id="999992", source="development_fixture"
    )
    session.add_all([first, second])
    session.flush()
    genes = []
    for symbol in ["AAA", "BBB", "CCC"]:
        gene = Gene(
            symbol=symbol,
            name="Synthetic " + symbol,
            organism_id=first.id,
            source="development_fixture",
            source_identifier="fixture-" + symbol,
        )
        session.add(gene)
        genes.append(gene)
    session.add(
        Gene(
            symbol="AAA",
            name="Other organism AAA",
            organism_id=second.id,
            source="development_fixture",
        )
    )
    session.flush()
    session.add_all(
        [
            GeneExternalIdentifier(gene_id=gene.id, namespace=namespace, accession=identifier)
            for gene, namespace, identifier in [
                (genes[0], "ncbi_gene", "123"),
                (genes[1], "ncbi_gene", "456"),
                (genes[0], "ensembl_gene", "ENSG00000123456"),
            ]
        ]
    )
    session.commit()
    return genes


def test_overlap_dedup_coverage_provenance_and_exact_sets(session: Session):
    genes = seed(session)
    before = session.scalar(select(func.count()).select_from(Gene))
    report = gene_overlap(
        session, [" AAA ", "BBB", "AAA", "UNKNOWN"], ["BBB", "CCC"], "symbol", "999991"
    )
    assert report.metrics.left_size == report.metrics.right_size == 2
    assert report.metrics.intersection_size == 1 and report.metrics.union_size == 3
    assert report.metrics.jaccard == pytest.approx(1 / 3)
    assert [r.symbol for r in report.shared] == ["BBB"]
    assert [r.symbol for r in report.left_only] == ["AAA"] and [
        r.symbol for r in report.right_only
    ] == ["CCC"]
    assert report.left.duplicates_removed == 1 and report.left.unresolved == ["UNKNOWN"]
    assert not report.coverage_complete and report.left.matched_inputs["AAA"] == genes[0].id
    assert report.shared[0].source == "development_fixture"
    assert report.shared[0].href.endswith("taxonomy_id=999991")
    assert (
        report.shared[0].resolved_identifier == "BBB"
        and report.shared[0].identifier_record_id is None
    )
    assert (
        report.method == "exact_local_gene_set_overlap_v1" and report.computed_at.tzinfo is not None
    )
    assert "p-value" in report.interpretation
    assert session.scalar(select(func.count()).select_from(Gene)) == before


def test_overlap_registry_taxonomy_case_and_empty_union(session: Session):
    genes = seed(session)
    report = gene_overlap(session, ["123", "456"], ["456"], "ncbi_gene", "999991")
    assert report.coverage_complete and report.metrics.jaccard == 0.5
    assert report.shared[0].id == genes[1].id and report.shared[0].identifier_record_id is not None
    assert report.shared[0].resolved_identifier == "456"
    ensembl = gene_overlap(
        session, ["ENSG00000123456"], ["ENSG00000123456"], "ensembl_gene", "999991"
    )
    assert ensembl.metrics.jaccard == 1 and ensembl.shared[0].id == genes[0].id
    wrong = gene_overlap(session, ["123"], ["456"], "ncbi_gene", "999992")
    assert (
        wrong.metrics.union_size == 0
        and wrong.metrics.jaccard is None
        and not wrong.coverage_complete
    )
    lower = gene_overlap(session, ["aaa"], ["AAA"], "symbol", "999991")
    assert lower.left.unresolved == ["aaa"] and lower.metrics.jaccard == 0
    single = gene_overlap(session, ["AAA"], ["AAA"], "symbol", "999992")
    assert single.shared[0].id != genes[0].id


@pytest.mark.parametrize(
    "values,namespace",
    [
        ([], "symbol"),
        (["AAA"] * 51, "symbol"),
        (["a" * 65], "symbol"),
        (["AAA OR *"], "symbol"),
        (["0"], "ncbi_gene"),
        (["ENSG00000123456.2"], "ensembl_gene"),
        (["P04637"], "ensembl_gene"),
    ],
)
def test_overlap_invalid_inputs_fail_closed(values, namespace):
    with pytest.raises(InvalidInputError):
        normalize_inputs(values, namespace)


def test_overlap_api_read_only_input_bounds_and_explicit_taxonomy(
    client: TestClient, session: Session
):
    seed(session)
    base = "/api/v1/analysis/gene-overlap"
    params = [("left", "AAA"), ("left", "BBB"), ("right", "BBB"), ("taxonomy_id", "999991")]
    response = client.get(base, params=params)
    assert response.status_code == 200 and response.json()["metrics"]["jaccard"] == 0.5
    assert client.get(base, params=[("left", "AAA"), ("right", "AAA")]).status_code == 422
    assert client.get(base, params=[*params, ("namespace", "protein")]).status_code == 422
    assert (
        client.get(
            base, params=[("left", "AAA")] * 51 + [("right", "AAA"), ("taxonomy_id", "999991")]
        ).status_code
        == 422
    )
    assert client.post(base, json={}).status_code == 405
