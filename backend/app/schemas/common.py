from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PatchModel(ApiModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            null_fields = sorted(
                field
                for field in cls.non_nullable_fields
                if field in value and value[field] is None
            )
            if null_fields:
                joined = ", ".join(null_fields)
                raise ValueError(f"These fields cannot be null when provided: {joined}")
        return value


class ProvenanceFields(ApiModel):
    source: str = Field(min_length=1, max_length=64)
    source_identifier: str | None = Field(default=None, max_length=255)
    source_url: HttpUrl | None = None
    imported_at: datetime | None = None


class StoredProvenanceFields(ProvenanceFields):
    id: int
    created_at: datetime
    updated_at: datetime


class Page[T](BaseModel):
    items: list[T]
    page: int
    page_size: int
    total: int
    pages: int


class ErrorBody(BaseModel):
    code: str
    message: str
    details: object | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
