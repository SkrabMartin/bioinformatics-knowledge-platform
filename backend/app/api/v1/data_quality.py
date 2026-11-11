from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession
from app.schemas.data_quality import QualityReport
from app.services.data_quality import DataQualityService

router = APIRouter(prefix="/data-quality", tags=["data quality"])


@router.get("", response_model=QualityReport)
def review_data_quality(
    session: DatabaseSession,
    refresh_after_days: Annotated[int, Query(ge=1, le=3650)] = 90,
) -> QualityReport:
    return DataQualityService(session).report(refresh_after_days)
