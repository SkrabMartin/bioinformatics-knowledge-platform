import re
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from app.schemas.common import ApiModel

ImportEntityType = Literal["gene", "protein", "publication", "dataset"]
JobStatus = Literal["queued", "running", "succeeded", "completed_with_errors", "cancelled"]
ItemStatus = Literal["pending", "running", "retry_wait", "succeeded", "failed", "cancelled"]


class ImportJobCreate(ApiModel):
    model_config = ConfigDict(extra="forbid")
    entity_type: ImportEntityType
    identifiers: list[str] = Field(min_length=1, max_length=100)
    taxonomy_id: str | None = Field(default=None, pattern=r"^[1-9][0-9]{0,15}$")
    max_attempts: int = Field(default=3, ge=1, le=5)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_identifiers(self) -> "ImportJobCreate":
        normalized = []
        for identifier in self.identifiers:
            identifier = identifier.strip()
            pattern = {
                "gene": r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}",
                "protein": r"[A-Za-z0-9]{6,10}",
                "publication": r"[1-9][0-9]{0,11}",
                "dataset": r"GSE[1-9][0-9]{0,15}",
            }[self.entity_type]
            if not re.fullmatch(pattern, identifier):
                raise ValueError("Invalid import identifier format.")
            normalized.append(identifier.upper() if self.entity_type == "protein" else identifier)
        self.identifiers = list(dict.fromkeys(normalized))
        if self.entity_type == "gene":
            if self.taxonomy_id is None:
                raise ValueError("Gene batches require an explicit taxonomy_id.")
        elif self.taxonomy_id is not None:
            raise ValueError("taxonomy_id is only supported for gene batches.")
        return self


class ImportJobRead(ApiModel):
    id: str
    entity_type: ImportEntityType
    taxonomy_id: str | None
    status: JobStatus
    max_attempts: int
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime
    counts: dict[str, int]


class ImportJobItemRead(ApiModel):
    id: int
    identifier: str
    status: ItemStatus
    attempts: int
    available_at: datetime
    result: dict[str, object] | None
    error_code: str | None
