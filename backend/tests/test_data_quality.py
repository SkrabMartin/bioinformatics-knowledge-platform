from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Gene, GeneExternalIdentifier, Organism, Protein
from app.services.data_quality import DataQualityService, QualityTimeout


def seed(session: Session, *, taxonomy: str | None = "999999") -> Gene:
    organism = Organism(
        scientific_name="Synthetic quality organism", taxonomy_id=taxonomy, source="test_source"
    )
    session.add(organism)
    session.flush()
    gene = Gene(symbol="TEST", name="Synthetic", organism_id=organism.id, source="test_source")
    session.add(gene)
    session.commit()
    return gene


def checks(session: Session, days: int = 90) -> dict:
    return {item.code: item for item in DataQualityService(session).report(days).checks}


def test_empty_report_and_input_bounds(client: TestClient) -> None:
    result = client.get("/api/v1/data-quality")
    assert result.status_code == 200
    assert len(result.json()["checks"]) == 10
    assert all(x["assessed"] == x["affected"] == 0 for x in result.json()["checks"])
    for days in ["0", "3651", "wrong"]:
        assert (
            client.get("/api/v1/data-quality", params={"refresh_after_days": days}).status_code
            == 422
        )


def test_missing_metadata_is_not_a_refresh_or_scientific_failure(session: Session) -> None:
    gene = seed(session)
    report = checks(session)
    assert report["gene_provenance"].affected == 1
    assert report["gene_refresh"].affected == 0
    assert report["gene_ensembl_coverage"].severity == "info"
    assert report["gene_provenance"].examples[0].href == "/gene/TEST?taxonomy_id=999999"
    assert session.get(Gene, gene.id).source_identifier is None


def test_refresh_window_and_complete_metadata(session: Session) -> None:
    gene = seed(session)
    gene.source_identifier = "SYNTHETIC"
    gene.source_url = "https://example.test/record"
    gene.imported_at = datetime.now(UTC) - timedelta(days=20)
    session.commit()
    assert checks(session, 10)["gene_refresh"].affected == 1
    report = checks(session, 90)
    assert report["gene_refresh"].affected == report["gene_provenance"].affected == 0


def test_fixture_exclusion_and_example_bound(session: Session) -> None:
    gene = seed(session)
    for i in range(8):
        session.add(
            Gene(
                symbol=f"TEST-{i}",
                name="Synthetic",
                organism_id=gene.organism_id,
                source="development_fixture" if i == 0 else "test_source",
            )
        )
    session.commit()
    result = checks(session)["gene_provenance"]
    assert result.assessed == result.affected == 8
    assert len(result.examples) == 5


def test_registry_conflict_and_missing_evidence_without_mutation(session: Session) -> None:
    gene = seed(session)
    session.add(
        GeneExternalIdentifier(
            gene_id=gene.id, namespace="ensembl_gene", accession="ENSG00000000001"
        )
    )
    session.commit()
    before = session.scalar(select(func.count()).select_from(GeneExternalIdentifier))
    report = checks(session)
    assert report["identifier_evidence"].affected == 1
    assert report["identifier_projection"].affected == 1
    assert report["gene_ensembl_coverage"].affected == 1
    assert session.get(Gene, gene.id).ensembl_gene_id is None
    assert session.scalar(select(func.count()).select_from(GeneExternalIdentifier)) == before


def test_protein_species_conflict_excludes_unlinked_proteins(session: Session) -> None:
    gene = seed(session)
    other = Organism(scientific_name="Other synthetic organism", source="test_source")
    session.add(other)
    session.flush()
    for accession, parent in [("TEST-A", gene.id), ("TEST-B", None)]:
        session.add(
            Protein(
                accession=accession,
                name="Synthetic",
                organism_id=other.id,
                gene_id=parent,
                source="test_source",
            )
        )
    session.commit()
    report = checks(session)
    assert report["protein_organism"].assessed == report["protein_organism"].affected == 1
    assert report["protein_organism"].examples[0].href == "/protein/TEST-A"


def test_missing_taxonomy_never_links_to_default_human_gene(session: Session) -> None:
    seed(session, taxonomy=None)
    assert checks(session)["gene_provenance"].examples[0].href is None


def test_expired_review_budget_fails_without_partial_report(session: Session) -> None:
    with (
        patch("app.services.data_quality.time.monotonic", side_effect=[0, 6]),
        pytest.raises(QualityTimeout),
    ):
        DataQualityService(session).report()
