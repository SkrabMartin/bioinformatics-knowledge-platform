from typing import Literal, Protocol

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.models import NormalizedGene, NormalizedOrganism, NormalizedProtein
from app.models import Gene, Organism, Protein
from app.repositories.genes import GeneRepository
from app.repositories.organisms import OrganismRepository
from app.repositories.proteins import ProteinRepository


class GeneProvider(Protocol):
    def fetch_gene(self, symbol: str, taxonomy_id: str = "9606") -> NormalizedGene: ...


class ProteinProvider(Protocol):
    def fetch_protein(self, accession: str) -> NormalizedProtein: ...


class ImportResult(BaseModel):
    entity_type: Literal["gene", "protein"]
    entity_id: int
    identifier: str
    action: Literal["created", "updated", "unchanged"]


class IngestionPersistenceError(RuntimeError):
    pass


class GeneIngestionService:
    def __init__(self, session: Session, provider: GeneProvider) -> None:
        self.session = session
        self.provider = provider
        self.genes = GeneRepository(session)
        self.organisms = OrganismRepository(session)

    def import_gene(self, symbol: str, taxonomy_id: str = "9606") -> ImportResult:
        record = self.provider.fetch_gene(symbol, taxonomy_id)
        try:
            organism = _upsert_organism(self.session, self.organisms, record.organism)
            gene_by_identifier = self.genes.by_external_identifier(record.ncbi_gene_id)
            gene_by_symbol = self.genes.by_organism_and_symbol(organism.id, record.symbol)
            if (
                gene_by_identifier is not None
                and gene_by_symbol is not None
                and gene_by_identifier.id != gene_by_symbol.id
            ):
                raise IngestionPersistenceError(
                    "The NCBI identifier and organism/symbol match different gene records."
                )
            gene = gene_by_identifier or gene_by_symbol
            if gene is None:
                gene = Gene(
                    symbol=record.symbol,
                    name=record.name,
                    description=record.description,
                    organism_id=organism.id,
                    chromosome=record.chromosome,
                    start_position=record.start_position,
                    end_position=record.end_position,
                    strand=record.strand,
                    ncbi_gene_id=record.ncbi_gene_id,
                    ensembl_gene_id=record.ensembl_gene_id,
                    source=record.provenance.source,
                    source_identifier=record.provenance.source_identifier,
                    source_url=str(record.provenance.source_url),
                    imported_at=record.provenance.retrieved_at,
                )
                self.session.add(gene)
                self.session.flush()
                action: Literal["created", "updated", "unchanged"] = "created"
            else:
                if (
                    gene.ncbi_gene_id not in (None, record.ncbi_gene_id)
                    and gene.source != "development_fixture"
                ):
                    raise IngestionPersistenceError(
                        f"Gene {gene.symbol} already has a different NCBI Gene identifier."
                    )
                changed = _update_gene(gene, record, organism.id)
                action = "updated" if changed else "unchanged"
            self.session.commit()
        except IngestionPersistenceError:
            self.session.rollback()
            raise
        except IntegrityError as exc:
            self.session.rollback()
            raise IngestionPersistenceError(
                "The normalized gene conflicts with an existing stable identifier."
            ) from exc
        return ImportResult(
            entity_type="gene",
            entity_id=gene.id,
            identifier=gene.symbol,
            action=action,
        )


class ProteinIngestionService:
    def __init__(self, session: Session, provider: ProteinProvider) -> None:
        self.session = session
        self.provider = provider
        self.proteins = ProteinRepository(session)
        self.genes = GeneRepository(session)
        self.organisms = OrganismRepository(session)

    def import_protein(self, accession: str) -> ImportResult:
        record = self.provider.fetch_protein(accession)
        try:
            organism = _upsert_organism(self.session, self.organisms, record.organism)
            gene = None
            if record.ncbi_gene_id:
                gene = self.genes.by_external_identifier(record.ncbi_gene_id)
            if gene is None and record.gene_symbol:
                gene = self.genes.by_organism_and_symbol(organism.id, record.gene_symbol)
            if gene is not None and gene.organism_id != organism.id:
                raise IngestionPersistenceError(
                    "The matching gene and UniProt protein belong to different organisms."
                )

            protein = self.proteins.by_accession(record.accession)
            if protein is None:
                protein = Protein(
                    accession=record.accession,
                    name=record.name,
                    gene_id=gene.id if gene else None,
                    organism_id=organism.id,
                    function=record.function,
                    sequence_length=record.sequence_length,
                    source=record.provenance.source,
                    source_identifier=record.provenance.source_identifier,
                    source_url=str(record.provenance.source_url),
                    imported_at=record.provenance.retrieved_at,
                )
                self.session.add(protein)
                self.session.flush()
                action: Literal["created", "updated", "unchanged"] = "created"
            else:
                changed = _update_protein(protein, record, organism.id, gene.id if gene else None)
                action = "updated" if changed else "unchanged"
            self.session.commit()
        except IngestionPersistenceError:
            self.session.rollback()
            raise
        except IntegrityError as exc:
            self.session.rollback()
            raise IngestionPersistenceError(
                "The normalized protein conflicts with an existing stable identifier."
            ) from exc
        return ImportResult(
            entity_type="protein",
            entity_id=protein.id,
            identifier=protein.accession,
            action=action,
        )


def _upsert_organism(
    session: Session,
    repository: OrganismRepository,
    record: NormalizedOrganism,
) -> Organism:
    organism = repository.by_taxonomy_id(record.taxonomy_id)
    if organism is None:
        organism = Organism(
            scientific_name=record.scientific_name,
            common_name=record.common_name,
            taxonomy_id=record.taxonomy_id,
            source=record.provenance.source,
            source_identifier=record.provenance.source_identifier,
            source_url=str(record.provenance.source_url),
            imported_at=record.provenance.retrieved_at,
        )
        session.add(organism)
        session.flush()
        return organism

    if organism.source in ("development_fixture", record.provenance.source):
        organism.scientific_name = record.scientific_name
        organism.common_name = record.common_name
        organism.source = record.provenance.source
        organism.source_identifier = record.provenance.source_identifier
        organism.source_url = str(record.provenance.source_url)
        organism.imported_at = record.provenance.retrieved_at
    elif organism.common_name is None and record.common_name is not None:
        organism.common_name = record.common_name
    return organism


def _update_gene(gene: Gene, record: NormalizedGene, organism_id: int) -> bool:
    values: dict[str, object] = {
        "symbol": record.symbol,
        "name": record.name,
        "description": record.description,
        "organism_id": organism_id,
        "chromosome": record.chromosome,
        "start_position": record.start_position,
        "end_position": record.end_position,
        "strand": record.strand,
        "ncbi_gene_id": record.ncbi_gene_id,
        "source": record.provenance.source,
        "source_identifier": record.provenance.source_identifier,
        "source_url": str(record.provenance.source_url),
    }
    if record.ensembl_gene_id is not None:
        values["ensembl_gene_id"] = record.ensembl_gene_id
    changed = any(getattr(gene, key) != value for key, value in values.items())
    for key, value in values.items():
        setattr(gene, key, value)
    gene.imported_at = record.provenance.retrieved_at
    return changed


def _update_protein(
    protein: Protein,
    record: NormalizedProtein,
    organism_id: int,
    gene_id: int | None,
) -> bool:
    values: dict[str, object] = {
        "accession": record.accession,
        "name": record.name,
        "gene_id": gene_id,
        "organism_id": organism_id,
        "function": record.function,
        "sequence_length": record.sequence_length,
        "source": record.provenance.source,
        "source_identifier": record.provenance.source_identifier,
        "source_url": str(record.provenance.source_url),
    }
    changed = any(getattr(protein, key) != value for key, value in values.items())
    for key, value in values.items():
        setattr(protein, key, value)
    protein.imported_at = record.provenance.retrieved_at
    return changed
