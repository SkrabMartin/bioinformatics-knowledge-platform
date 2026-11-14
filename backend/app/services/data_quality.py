"""Bounded diagnostics of stored metadata; no upstream calls or biological scoring."""

import time
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import quote

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import Gene, GeneExternalIdentifier, Organism, Protein, Transcript
from app.schemas.data_quality import QualityCheck, QualityExample, QualityReport
from app.services.errors import ApplicationError


class QualityTimeout(ApplicationError):
    status_code = 503
    code = "quality_timeout"


class DataQualityService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def report(self, refresh_after_days: int = 90) -> QualityReport:
        started = datetime.now(UTC)
        deadline = time.monotonic() + 5
        checks: list[QualityCheck] = []

        def execute(statement: Select[Any]) -> Any:
            remaining = int((deadline - time.monotonic()) * 1000)
            if remaining <= 0:
                raise QualityTimeout(
                    "Data quality review exceeded its time budget. Try again later."
                )
            connection = self.session.connection()
            if connection.dialect.name == "postgresql":
                connection.exec_driver_sql(
                    "SELECT set_config('statement_timeout', %s, true)", (f"{remaining}ms",)
                )
            try:
                return self.session.execute(statement)
            except DBAPIError as exc:
                if getattr(exc.orig, "sqlstate", None) == "57014":
                    raise QualityTimeout("Data quality review timed out. Try again later.") from exc
                raise

        def check(
            code: str,
            title: str,
            severity: Literal["info", "warning", "error"],
            explanation: str,
            base: Select[Any],
            condition: Any,
            kind: str,
        ) -> None:
            assessed = execute(select(func.count()).select_from(base.subquery())).scalar_one()
            affected_query = base.where(condition)
            affected = execute(
                select(func.count()).select_from(affected_query.subquery())
            ).scalar_one()
            rows = execute(affected_query.order_by("id").limit(5)).all()
            examples = []
            for row in rows:
                href = (
                    f"/gene/{quote(row.label, safe='')}?taxonomy_id={quote(row.taxonomy, safe='')}"
                    if kind == "gene" and row.taxonomy
                    else None
                    if kind == "gene"
                    else f"/{kind}/{quote(row.label, safe='')}"
                )
                examples.append(QualityExample(id=row.id, label=row.label, href=href))
            checks.append(
                QualityCheck(
                    code=code,
                    title=title,
                    severity=severity,
                    explanation=explanation,
                    assessed=assessed,
                    affected=affected,
                    examples=examples,
                )
            )

        genes = (
            select(Gene.id, Gene.symbol.label("label"), Organism.taxonomy_id.label("taxonomy"))
            .join(Organism, Gene.organism_id == Organism.id)
            .where(Gene.source != "development_fixture")
        )
        proteins = select(Protein.id, Protein.accession.label("label")).where(
            Protein.source != "development_fixture"
        )
        transcripts = (
            select(Transcript.id, Transcript.ensembl_transcript_id.label("label"))
            .join(Gene, Transcript.gene_id == Gene.id)
            .where(Gene.source != "development_fixture", Transcript.source != "development_fixture")
        )
        entities: list[tuple[type[Gene] | type[Protein] | type[Transcript], Select[Any], str]] = [
            (Gene, genes, "gene"),
            (Protein, proteins, "protein"),
            (Transcript, transcripts, "transcript"),
        ]
        for model, base, kind in entities:
            missing = or_(
                func.trim(model.source) == "",
                model.source_identifier.is_(None),
                func.trim(model.source_identifier) == "",
                model.source_url.is_(None),
                func.trim(model.source_url) == "",
                model.imported_at.is_(None),
            )
            check(
                f"{kind}_provenance",
                f"{kind.title()} source metadata",
                "warning",
                "Source name, record identifier, URL or retrieval time is missing. This does not "
                "establish that the biological record is incorrect.",
                base,
                missing,
                kind,
            )
            check(
                f"{kind}_refresh",
                f"{kind.title()} refresh review",
                "info",
                "Retrieval is older than the selected interval. This is a refresh reminder, not "
                "proof that the source or biology is outdated. Missing retrieval times are "
                "counted under source metadata.",
                base,
                model.imported_at < started - timedelta(days=refresh_after_days),
                kind,
            )
        check(
            "gene_ensembl_coverage",
            "Verified Ensembl mapping coverage",
            "info",
            "Genes without a source-evidenced Ensembl identity. Absence is a coverage gap, "
            "not a biological error or a reason to infer a mapping.",
            genes,
            ~Gene.external_identifiers.any(
                (GeneExternalIdentifier.namespace == "ensembl_gene")
                & GeneExternalIdentifier.evidence.any()
            ),
            "gene",
        )
        check(
            "identifier_evidence",
            "Identifier evidence coverage",
            "warning",
            "Genes with registered identifiers that have no source assertion.",
            genes,
            Gene.external_identifiers.any(~GeneExternalIdentifier.evidence.any()),
            "gene",
        )
        check(
            "identifier_projection",
            "Identifier consistency",
            "error",
            "A registered primary identity differs from the corresponding legacy field, or "
            "that field is missing. Review before reimport; no automatic correction is "
            "applied.",
            genes,
            Gene.external_identifiers.any(
                or_(
                    (GeneExternalIdentifier.namespace == "ncbi_gene")
                    & or_(
                        Gene.ncbi_gene_id.is_(None),
                        GeneExternalIdentifier.accession != Gene.ncbi_gene_id,
                    ),
                    (GeneExternalIdentifier.namespace == "ensembl_gene")
                    & or_(
                        Gene.ensembl_gene_id.is_(None),
                        GeneExternalIdentifier.accession != Gene.ensembl_gene_id,
                    ),
                )
            ),
            "gene",
        )
        check(
            "protein_organism",
            "Protein / gene organism consistency",
            "error",
            "Linked protein and gene have different stored organism IDs. Unlinked proteins "
            "are not treated as errors.",
            proteins.join(Gene, Protein.gene_id == Gene.id).where(
                Gene.source != "development_fixture"
            ),
            Protein.organism_id != Gene.organism_id,
            "protein",
        )
        return QualityReport(
            started_at=started,
            completed_at=datetime.now(UTC),
            refresh_after_days=refresh_after_days,
            checks=checks,
        )
