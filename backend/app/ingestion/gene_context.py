"""Preserve explicit source observations; never infer assemblies or retire missing assertions."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.errors import IngestionPersistenceError
from app.ingestion.models import NormalizedGene
from app.models.gene import Gene
from app.models.gene_context import GeneAlias, GeneGenomicLocation

MAX_CONTEXT_RECORDS = 500


def store_gene_context(session: Session, gene: Gene, record: NormalizedGene) -> bool:
    provenance = {
        "source": record.provenance.source,
        "source_identifier": record.provenance.source_identifier,
        "source_url": str(record.provenance.source_url),
        "imported_at": record.provenance.retrieved_at,
    }
    aliases = {
        item.alias: item
        for item in session.scalars(
            select(GeneAlias).where(
                GeneAlias.gene_id == gene.id, GeneAlias.source == provenance["source"]
            )
        )
    }
    locations = {
        (item.sequence_accession, item.start_position, item.end_position, item.strand): item
        for item in session.scalars(
            select(GeneGenomicLocation).where(
                GeneGenomicLocation.gene_id == gene.id,
                GeneGenomicLocation.source == provenance["source"],
            )
        )
    }
    changed = False
    for alias in record.aliases:
        item = aliases.get(alias)
        if item is None:
            item = GeneAlias(gene_id=gene.id, alias=alias, **provenance)
            session.add(item)
            aliases[alias] = item
            changed = True
        else:
            item.imported_at = record.provenance.retrieved_at
    for location in record.genomic_locations:
        key = (
            location.sequence_accession,
            location.start_position,
            location.end_position,
            location.strand,
        )
        placement = locations.get(key)
        if placement is None:
            placement = GeneGenomicLocation(gene_id=gene.id, **location.model_dump(), **provenance)
            session.add(placement)
            locations[key] = placement
            changed = True
        else:
            # The accession and coordinates identify the observation. A changed
            # chromosome label is metadata, never a new assembly inference.
            changed = changed or placement.chromosome != location.chromosome
            placement.chromosome = location.chromosome
            placement.imported_at = record.provenance.retrieved_at
    if len(aliases) > MAX_CONTEXT_RECORDS or len(locations) > MAX_CONTEXT_RECORDS:
        raise IngestionPersistenceError(
            "Gene source context exceeds the retained-observation limit."
        )
    return changed
