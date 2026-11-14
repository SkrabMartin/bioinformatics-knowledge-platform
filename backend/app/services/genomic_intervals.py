import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.engine import Result
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.models import Gene, Organism, Transcript
from app.schemas.common import Page
from app.schemas.genomic_interval import IntervalQuery, IntervalReport, TranscriptOverlap
from app.schemas.transcript import TranscriptSummary
from app.services.errors import ApplicationError


class IntervalTimeout(ApplicationError):
    status_code = 503
    code = "genomic_interval_timeout"


class GenomicIntervalService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _execute(self, statement: Select[Any]) -> Result[Any]:
        remaining = int((self.deadline - time.monotonic()) * 1000)
        if remaining <= 0:
            raise IntervalTimeout("Interval query exceeded its time budget. Narrow the interval.")
        if self.session.get_bind().dialect.name == "postgresql":
            self.session.connection().exec_driver_sql(
                "SELECT set_config('statement_timeout', %s, true)", (f"{remaining}ms",)
            )
        try:
            return self.session.execute(statement)
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "57014":
                raise IntervalTimeout("Interval query timed out. Narrow the interval.") from exc
            raise

    def browse(self, query: IntervalQuery) -> IntervalReport:
        page, page_size = query.page, query.page_size
        self.deadline = time.monotonic() + 3
        statement = (
            select(Transcript, Gene.symbol)
            .join(Gene, Gene.id == Transcript.gene_id)
            .join(Organism, Organism.id == Gene.organism_id)
            .where(
                Organism.taxonomy_id == query.taxonomy_id,
                Transcript.assembly_name == query.assembly_name,
                Transcript.sequence_region == query.sequence_region,
                Transcript.start_position <= query.end,
                Transcript.end_position >= query.closed_start,
            )
        )
        if query.strand:
            statement = statement.where(Transcript.strand == query.strand)
        total = self._execute(select(func.count()).select_from(statement.subquery())).scalar_one()
        rows = self._execute(
            statement.order_by(
                Transcript.start_position,
                Transcript.end_position,
                Transcript.ensembl_transcript_id,
                Transcript.id,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        items = []
        for record, symbol in rows:
            start, end = (
                max(record.start_position, query.closed_start),
                min(record.end_position, query.end),
            )
            items.append(
                TranscriptOverlap(
                    **TranscriptSummary.model_validate(record).model_dump(),
                    gene_id=record.gene_id,
                    gene_symbol=symbol,
                    gene_href=f"/gene/{quote(symbol, safe='')}?taxonomy_id={query.taxonomy_id}",
                    transcript_href=f"/transcript/{quote(record.ensembl_transcript_id, safe='')}",
                    overlap_start=start,
                    overlap_end=end,
                    overlap_bases=end - start + 1,
                )
            )
        return IntervalReport(
            observed_at=datetime.now(UTC),
            query=query,
            normalized_start=query.closed_start,
            normalized_end=query.end,
            matches=Page(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
                pages=(total + page_size - 1) // page_size,
            ),
        )
