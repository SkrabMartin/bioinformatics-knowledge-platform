from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession
from app.schemas.genomic_interval import IntervalQuery, IntervalReport
from app.services.genomic_intervals import GenomicIntervalService

router = APIRouter(prefix="/genomics", tags=["genomics"])


@router.get("/transcript-overlaps", response_model=IntervalReport)
def transcript_overlaps(
    session: DatabaseSession,
    interval: Annotated[IntervalQuery, Query()],
) -> IntervalReport:
    return GenomicIntervalService(session).browse(interval)
