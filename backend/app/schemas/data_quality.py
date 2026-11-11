from datetime import datetime
from typing import Literal

from app.schemas.common import ApiModel


class QualityExample(ApiModel):
    id: int
    label: str
    href: str | None


class QualityCheck(ApiModel):
    code: str
    title: str
    severity: Literal["info", "warning", "error"]
    explanation: str
    assessed: int
    affected: int
    examples: list[QualityExample]


class QualityReport(ApiModel):
    started_at: datetime
    completed_at: datetime
    refresh_after_days: int
    fixture_policy: str = "Exclude development_fixture records and their child assertions."
    scope: str = "Genes, proteins, transcripts and gene identifier assertions only."
    checks: list[QualityCheck]
