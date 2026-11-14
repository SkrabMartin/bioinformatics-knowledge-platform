from sqlalchemy import select

from app.core.identifiers import canonical_gene_identifier
from app.models import Gene, GeneExternalIdentifier, GeneIdentifierEvidence
from app.repositories.genes import GeneRepository
from app.services.errors import InvalidInputError, NotFoundError


def resolve_gene_identifier(repository: GeneRepository, namespace: str, requested: str) -> Gene:
    try:
        accession = canonical_gene_identifier(namespace, requested)
    except ValueError as exc:
        raise InvalidInputError("Invalid gene identifier namespace or format.") from exc
    query = select(GeneExternalIdentifier).where(
        GeneExternalIdentifier.namespace == namespace,
        GeneExternalIdentifier.accession == accession,
    )
    if requested.strip() != accession:
        query = query.where(
            GeneExternalIdentifier.evidence.any(
                GeneIdentifierEvidence.reported_accession == requested.strip()
            )
        )
    identity = repository.session.scalar(query)
    if identity is None:
        raise NotFoundError("No source-backed mapping is stored for this identifier.")
    gene = repository.get(identity.gene_id)
    if gene is None:
        raise NotFoundError("The mapped gene is not stored locally.")
    return gene
