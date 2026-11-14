from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.identifiers import canonical_gene_identifier
from app.ingestion.errors import IngestionPersistenceError
from app.ingestion.models import SourceProvenance
from app.models.gene import Gene
from app.models.gene_identifier import GeneExternalIdentifier, GeneIdentifierEvidence

MAX_IDENTIFIER_EVIDENCE = 200


def record_gene_identifier(
    session: Session,
    gene: Gene,
    namespace: str,
    reported: str,
    provenance: SourceProvenance,
    *,
    source_record_version: str | None = None,
) -> bool:
    """Caller owns the gene row lock and commits the entire import atomically."""
    try:
        accession = canonical_gene_identifier(namespace, reported)
    except ValueError as exc:
        raise IngestionPersistenceError("Provider supplied an invalid gene identifier.") from exc
    legacy_field = "ncbi_gene_id" if namespace == "ncbi_gene" else "ensembl_gene_id"
    legacy = getattr(gene, legacy_field)
    if legacy is not None and legacy != accession:
        raise IngestionPersistenceError(
            "Source mapping conflicts with the gene's primary identifier."
        )
    identity = session.scalar(
        select(GeneExternalIdentifier).where(
            GeneExternalIdentifier.namespace == namespace,
            GeneExternalIdentifier.accession == accession,
        )
    )
    if identity is not None and identity.gene_id != gene.id:
        raise IngestionPersistenceError(
            "External identifier already belongs to another local gene."
        )
    changed = False
    if identity is None:
        occupied = session.scalar(
            select(GeneExternalIdentifier.id).where(
                GeneExternalIdentifier.gene_id == gene.id,
                GeneExternalIdentifier.namespace == namespace,
            )
        )
        if occupied is not None:
            raise IngestionPersistenceError(
                "Gene already has another identifier in this namespace."
            )
        identity = GeneExternalIdentifier(gene_id=gene.id, namespace=namespace, accession=accession)
        session.add(identity)
        session.flush()
        changed = True
    if legacy is None:
        setattr(gene, legacy_field, accession)
        changed = True
    evidence = session.scalar(
        select(GeneIdentifierEvidence).where(
            GeneIdentifierEvidence.identifier_id == identity.id,
            GeneIdentifierEvidence.source == provenance.source,
            GeneIdentifierEvidence.source_identifier == provenance.source_identifier,
            GeneIdentifierEvidence.reported_accession == reported,
        )
    )
    if evidence is None:
        evidence = GeneIdentifierEvidence(
            identifier_id=identity.id,
            source=provenance.source,
            source_identifier=provenance.source_identifier,
            reported_accession=reported,
            source_url=str(provenance.source_url),
            source_record_version=source_record_version,
            imported_at=provenance.retrieved_at,
        )
        session.add(evidence)
        changed = True
    else:
        changed = changed or (
            evidence.source_record_version != source_record_version
            or evidence.source_url != str(provenance.source_url)
        )
        evidence.source_record_version = source_record_version
        evidence.source_url = str(provenance.source_url)
        evidence.imported_at = provenance.retrieved_at
    session.flush()
    count = (
        session.scalar(
            select(func.count())
            .select_from(GeneIdentifierEvidence)
            .where(GeneIdentifierEvidence.identifier_id == identity.id)
        )
        or 0
    )
    if count > MAX_IDENTIFIER_EVIDENCE:
        raise IngestionPersistenceError("Gene identifier evidence limit exceeded.")
    return changed
