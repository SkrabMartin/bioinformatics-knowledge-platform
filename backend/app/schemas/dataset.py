import re
from datetime import date, datetime
from typing import Literal

from pydantic import AwareDatetime, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.schemas.common import ProvenanceFields, StoredProvenanceFields


class DatasetCreate(ProvenanceFields):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)
    repository: Literal["GEO"]
    accession: str = Field(pattern=r"^GSE[1-9][0-9]{0,15}$")
    title: str = Field(min_length=1, max_length=20000)
    description: str | None = Field(default=None, max_length=200000)
    experiment_types: list[str] = Field(default_factory=list, max_length=100)
    organism_names: list[str] = Field(default_factory=list, max_length=100)
    taxonomy_ids: list[str] = Field(default_factory=list, max_length=100)
    platform_accessions: list[str] = Field(default_factory=list, max_length=1000)
    publication_pmids: list[str] = Field(default_factory=list, max_length=1000)
    sample_count: int | None = Field(default=None, ge=0, le=100000, strict=True)
    source_updated_date: date
    source_identifier: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl = Field(max_length=2048)
    imported_at: AwareDatetime

    @field_validator(
        "experiment_types",
        "organism_names",
        "taxonomy_ids",
        "platform_accessions",
        "publication_pmids",
    )
    @classmethod
    def bounded_values(cls, values: list[str]) -> list[str]:
        result = []
        for value in values:
            value = " ".join(value.split())
            if not value or len(value) > 512:
                raise ValueError("Dataset metadata values require 1-512 characters.")
            if value not in result:
                result.append(value)
        return result

    @model_validator(mode="after")
    def source_identity(self) -> "DatasetCreate":
        if self.source_identifier != self.accession:
            raise ValueError("GEO source identity must equal the series accession.")
        for values, pattern in [
            (self.taxonomy_ids, r"[1-9][0-9]{0,15}"),
            (self.platform_accessions, r"GPL[1-9][0-9]{0,15}"),
            (self.publication_pmids, r"[1-9][0-9]{0,31}"),
        ]:
            if any(not re.fullmatch(pattern, value) for value in values):
                raise ValueError("Dataset metadata contains invalid biological identifiers.")
        return self


class DatasetRead(DatasetCreate, StoredProvenanceFields):
    imported_at: datetime
