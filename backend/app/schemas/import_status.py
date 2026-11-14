from datetime import datetime
from typing import Literal

from app.schemas.common import ApiModel
from app.schemas.import_job import ImportEntityType


class ImportActivity(ApiModel):
    entity_type: ImportEntityType
    jobs: dict[str, int]
    items: dict[str, int]
    last_activity_at: datetime | None


class ImportStatusRead(ApiModel):
    observed_at: datetime
    worker_status: Literal["unknown"] = "unknown"
    scope: str = "Stored queue counts only; direct CLI imports are not recorded as jobs."
    activity: list[ImportActivity]
