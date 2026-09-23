from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.models import (
    NormalizedGene,
    NormalizedOrganism,
    NormalizedProtein,
    SourceProvenance,
)
from app.ingestion.services import GeneIngestionService, ProteinIngestionService
from app.models import Gene, Organism, Protein


def provenance(source: str, identifier: str, url: str) -> SourceProvenance:
    return SourceProvenance(
        source=source,  # type: ignore[arg-type]
        source_identifier=identifier,
        source_url=url,
        retrieved_at=datetime(2026, 9, 20, tzinfo=UTC),
    )


def normalized_organism(source: str = "NCBI Gene") -> NormalizedOrganism:
    return NormalizedOrganism(
        scientific_name="Homo sapiens",
        common_name="Human",
        taxonomy_id="9606",
        provenance=provenance(source, "9606", "https://example.test/taxonomy/9606"),
    )


class FakeGeneProvider:
    def fetch_gene(self, symbol: str, taxonomy_id: str = "9606") -> NormalizedGene:
        assert taxonomy_id == "9606"
        return NormalizedGene(
            symbol=symbol.upper(),
            name="tumor protein p53",
            description="Mocked NCBI description.",
            organism=normalized_organism(),
            chromosome="17",
            start_position=7668422,
            end_position=7687491,
            strand="-",
            ncbi_gene_id="7157",
            ensembl_gene_id=None,
            provenance=provenance("NCBI Gene", "7157", "https://example.test/gene/7157"),
        )


class FakeProteinProvider:
    def fetch_protein(self, accession: str) -> NormalizedProtein:
        assert accession.upper() == "P04637"
        return NormalizedProtein(
            accession="P04637",
            name="Cellular tumor antigen p53",
            function="Mocked UniProt function.",
            sequence_length=393,
            gene_symbol="TP53",
            ncbi_gene_id="7157",
            organism=normalized_organism("UniProt"),
            provenance=provenance("UniProt", "P04637", "https://example.test/uniprot/P04637"),
        )


def test_gene_import_is_idempotent(session: Session) -> None:
    service = GeneIngestionService(session, FakeGeneProvider())

    first = service.import_gene("TP53")
    second = service.import_gene("TP53")

    assert first.action == "created"
    assert second.action == "unchanged"
    assert first.entity_id == second.entity_id
    assert session.scalar(select(func.count()).select_from(Gene)) == 1
    assert session.scalar(select(func.count()).select_from(Organism)) == 1
    gene = session.scalar(select(Gene))
    assert gene is not None
    assert gene.source == "NCBI Gene"
    assert gene.source_identifier == "7157"


def test_protein_import_links_existing_gene_and_is_idempotent(session: Session) -> None:
    gene_result = GeneIngestionService(session, FakeGeneProvider()).import_gene("TP53")
    service = ProteinIngestionService(session, FakeProteinProvider())

    first = service.import_protein("P04637")
    second = service.import_protein("P04637")

    assert first.action == "created"
    assert second.action == "unchanged"
    assert first.entity_id == second.entity_id
    assert session.scalar(select(func.count()).select_from(Protein)) == 1
    protein = session.scalar(select(Protein))
    assert protein is not None
    assert protein.gene_id == gene_result.entity_id
    assert protein.source == "UniProt"
