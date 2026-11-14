import re
from datetime import UTC, datetime
from urllib.parse import quote

from sqlalchemy import literal, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import Gene, GeneExternalIdentifier, Organism
from app.schemas.gene_overlap import (
    GeneOverlapRead,
    OverlapGene,
    OverlapInput,
    OverlapMetrics,
    OverlapNamespace,
)
from app.services.errors import ApplicationError, InvalidInputError


class AnalysisTimeout(ApplicationError):
    status_code = 503
    code = "analysis_timeout"


def normalize_inputs(values: list[str], namespace: OverlapNamespace) -> list[str]:
    if not 1 <= len(values) <= 50:
        raise InvalidInputError("Each list requires 1-50 identifiers.")
    pattern = {
        "symbol": r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}",
        "ncbi_gene": r"[1-9][0-9]{0,15}",
        "ensembl_gene": r"ENS[A-Z]*G[0-9]{6,20}",
    }[namespace]
    normalized = [value.strip() for value in values]
    if any(len(value) > 64 or not re.fullmatch(pattern, value) for value in normalized):
        raise InvalidInputError(
            "Invalid exact identifier. "
            "Ensembl versions, aliases and fuzzy resolution are not supported."
        )
    return normalized


def gene_overlap(
    session: Session,
    left: list[str],
    right: list[str],
    namespace: OverlapNamespace,
    taxonomy_id: str,
) -> GeneOverlapRead:
    if not re.fullmatch(r"[1-9][0-9]{0,15}", taxonomy_id):
        raise InvalidInputError("An explicit positive taxonomy identifier is required.")
    left_values, right_values = (
        normalize_inputs(left, namespace),
        normalize_inputs(right, namespace),
    )
    inputs = list(dict.fromkeys([*left_values, *right_values]))
    identity = Gene.symbol if namespace == "symbol" else GeneExternalIdentifier.accession
    statement = (
        select(
            Gene,
            identity.label("input_identifier"),
            (literal(None) if namespace == "symbol" else GeneExternalIdentifier.id).label(
                "registry_id"
            ),
        )
        .join(Organism, Organism.id == Gene.organism_id)
        .where(Organism.taxonomy_id == taxonomy_id, identity.in_(inputs))
    )
    if namespace != "symbol":
        statement = statement.join(
            GeneExternalIdentifier, GeneExternalIdentifier.gene_id == Gene.id
        ).where(GeneExternalIdentifier.namespace == namespace)
    # One bounded identity query. No source calls or inference from names/aliases.
    if session.get_bind().dialect.name == "postgresql":
        session.connection().exec_driver_sql(
            "SELECT set_config('statement_timeout', %s, true)", ("3000ms",)
        )
    try:
        rows = session.execute(statement).all()
    except DBAPIError as exc:
        if getattr(exc.orig, "sqlstate", None) == "57014":
            raise AnalysisTimeout("Gene list resolution timed out. Retry a smaller list.") from exc
        raise
    mapping = {identifier: gene.id for gene, identifier, _ in rows}
    records = {
        gene.id: OverlapGene(
            id=gene.id,
            symbol=gene.symbol,
            name=gene.name,
            href=f"/gene/{quote(gene.symbol, safe='')}?taxonomy_id={taxonomy_id}",
            resolved_identifier=identifier,
            identifier_record_id=record_id,
            source=gene.source,
            source_identifier=gene.source_identifier,
            source_url=gene.source_url,
            imported_at=gene.imported_at,
            updated_at=gene.updated_at,
        )
        for gene, identifier, record_id in rows
    }

    def resolve(values: list[str]) -> OverlapInput:
        unique = list(dict.fromkeys(values))
        matched = {value: mapping[value] for value in unique if value in mapping}
        return OverlapInput(
            input_count=len(values),
            unique_inputs=unique,
            duplicates_removed=len(values) - len(unique),
            unresolved=[value for value in unique if value not in mapping],
            matched_inputs=matched,
            resolved_gene_count=len(set(matched.values())),
        )

    first, second = resolve(left_values), resolve(right_values)
    left_ids, right_ids = set(first.matched_inputs.values()), set(second.matched_inputs.values())
    shared, union = left_ids & right_ids, left_ids | right_ids

    def ordered(ids: set[int]) -> list[OverlapGene]:
        return sorted((records[id_] for id_ in ids), key=lambda record: (record.symbol, record.id))

    return GeneOverlapRead(
        computed_at=datetime.now(UTC),
        namespace=namespace,
        taxonomy_id=taxonomy_id,
        coverage_complete=not first.unresolved and not second.unresolved,
        left=first,
        right=second,
        metrics=OverlapMetrics(
            left_size=len(left_ids),
            right_size=len(right_ids),
            intersection_size=len(shared),
            union_size=len(union),
            jaccard=len(shared) / len(union) if union else None,
        ),
        shared=ordered(shared),
        left_only=ordered(left_ids - right_ids),
        right_only=ordered(right_ids - left_ids),
    )
