import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Gene, Organism, Protein


class FixtureError(RuntimeError):
    pass


def _load_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FixtureError(f"Fixture file does not exist: {path}")
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise FixtureError("Fixture document must be a JSON object.")
    document = cast(dict[str, Any], parsed)
    if document.get("fixture_type") != "development_demo":
        raise FixtureError("Refusing to load a fixture not marked as development_demo.")
    return document


def load_development_fixtures(session: Session, path: Path) -> dict[str, int]:
    """Idempotently load explicitly marked, non-authoritative demo records."""

    document = _load_document(path)
    counts = {"organisms_created": 0, "genes_created": 0, "proteins_created": 0}
    imported_at = datetime.now(UTC)
    organisms: dict[str, Organism] = {}
    genes: dict[str, Gene] = {}

    for record in document.get("organisms", []):
        taxonomy_id = record["taxonomy_id"]
        organism = session.scalar(select(Organism).where(Organism.taxonomy_id == taxonomy_id))
        if organism is None:
            organism = Organism(**record, imported_at=imported_at)
            session.add(organism)
            session.flush()
            counts["organisms_created"] += 1
        organisms[taxonomy_id] = organism

    for record in document.get("genes", []):
        data = dict(record)
        taxonomy_id = data.pop("organism_taxonomy_id")
        organism = organisms.get(taxonomy_id)
        if organism is None:
            raise FixtureError(f"Gene references unknown fixture taxonomy ID: {taxonomy_id}")
        gene = session.scalar(
            select(Gene).where(
                Gene.organism_id == organism.id,
                Gene.symbol == data["symbol"],
            )
        )
        if gene is None:
            gene = Gene(**data, organism_id=organism.id, imported_at=imported_at)
            session.add(gene)
            session.flush()
            counts["genes_created"] += 1
        genes[data["symbol"]] = gene

    for record in document.get("proteins", []):
        data = dict(record)
        taxonomy_id = data.pop("organism_taxonomy_id")
        gene_symbol = data.pop("gene_symbol", None)
        organism = organisms.get(taxonomy_id)
        if organism is None:
            raise FixtureError(f"Protein references unknown fixture taxonomy ID: {taxonomy_id}")
        gene = genes.get(gene_symbol) if gene_symbol else None
        if gene_symbol and gene is None:
            raise FixtureError(f"Protein references unknown fixture gene: {gene_symbol}")
        protein = session.scalar(select(Protein).where(Protein.accession == data["accession"]))
        if protein is None:
            session.add(
                Protein(
                    **data,
                    organism_id=organism.id,
                    gene_id=gene.id if gene else None,
                    imported_at=imported_at,
                )
            )
            session.flush()
            counts["proteins_created"] += 1

    session.commit()
    return counts
