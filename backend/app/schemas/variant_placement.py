from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, Field, HttpUrl, field_validator, model_validator

from app.schemas.common import ProvenanceFields, StoredProvenanceFields


class VariantPlacementCreate(ProvenanceFields):
    assembly_name: str = Field(min_length=1, max_length=128)
    assembly_accession: str | None = Field(
        default=None, pattern=r"^GC[AF]_[0-9]{9}\.[1-9][0-9]*$", max_length=32
    )
    sequence_accession: str = Field(
        min_length=1, max_length=128, pattern=r"^[A-Za-z][A-Za-z0-9_]{0,110}\.[1-9][0-9]{0,8}$"
    )
    sequence_region: str | None = Field(default=None, min_length=1, max_length=128)
    taxonomy_id: str = Field(pattern=r"^[1-9][0-9]{0,15}$", max_length=16)
    coordinate_system: Literal["one_based_closed"]
    strand: Literal["+"]
    start_position: int = Field(ge=1, le=9223372036854775807, strict=True)
    end_position: int = Field(ge=1, le=9223372036854775807, strict=True)
    reference_allele: str = Field(min_length=1, max_length=1000, pattern=r"^[ACGTN]+$")
    alternate_allele: str = Field(min_length=1, max_length=1000, pattern=r"^[ACGTN]+$")
    source_identifier: str = Field(min_length=1, max_length=255)
    source_release: str = Field(min_length=1, max_length=128)
    source_url: HttpUrl = Field(max_length=2048)
    imported_at: AwareDatetime

    @field_validator("reference_allele", "alternate_allele", mode="before")
    @classmethod
    def uppercase_alleles(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @field_validator(
        "source",
        "source_identifier",
        "source_release",
        "assembly_name",
        "sequence_accession",
        "sequence_region",
    )
    @classmethod
    def nonblank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Source and reference labels cannot be blank.")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_span(self) -> "VariantPlacementCreate":
        if self.end_position - self.start_position + 1 != len(self.reference_allele):
            raise ValueError("Closed reference span must equal the reference allele length.")
        if self.reference_allele == self.alternate_allele:
            raise ValueError("Reference and alternate alleles must differ.")
        return self


class VariantPlacementRead(VariantPlacementCreate, StoredProvenanceFields):
    imported_at: datetime
    variant_id: int
