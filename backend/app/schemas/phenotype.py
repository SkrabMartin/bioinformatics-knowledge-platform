from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, Field, HttpUrl, field_validator

from app.schemas.common import ProvenanceFields, StoredProvenanceFields
from app.schemas.disease import DiseaseRead


class SourcedPhenotypeFields(ProvenanceFields):
    source_identifier: str = Field(min_length=1, max_length=255)
    source_release: str = Field(min_length=1, max_length=128)
    source_url: HttpUrl = Field(max_length=2048)
    imported_at: AwareDatetime

    @field_validator("source", "source_identifier", "source_release")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Source fields cannot be blank.")
        return value.strip()


class PhenotypeCreate(SourcedPhenotypeFields):
    hpo_id: str = Field(pattern=r"^HP:[0-9]{7}$", max_length=10)
    name: str = Field(min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=20000)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name cannot be blank.")
        return value.strip()


class PhenotypeRead(PhenotypeCreate, StoredProvenanceFields):
    imported_at: datetime


class DiseasePhenotypeCreate(SourcedPhenotypeFields):
    phenotype_id: int = Field(gt=0, le=9223372036854775807)
    qualifier: Literal["present", "excluded"]
    evidence_kind: Literal["curated", "structured_metadata"]
    evidence_code: str | None = Field(default=None, min_length=1, max_length=32)
    reference: str = Field(min_length=1, max_length=255)

    @field_validator("reference")
    @classmethod
    def nonblank_reference(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reference cannot be blank.")
        return value.strip()


class DiseasePhenotypeRead(DiseasePhenotypeCreate, StoredProvenanceFields):
    imported_at: datetime
    disease_id: int
    phenotype: PhenotypeRead
    disease: DiseaseRead
