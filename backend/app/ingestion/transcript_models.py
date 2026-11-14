from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.ingestion.models import NormalizedModel

ENSEMBL_GENE_PATTERN = r"^ENS[A-Z]*G[0-9]{6,20}$"
ENSEMBL_TRANSCRIPT_PATTERN = r"^ENS[A-Z]*T[0-9]{6,20}$"


class NormalizedTranscript(NormalizedModel):
    ensembl_transcript_id: str = Field(pattern=ENSEMBL_TRANSCRIPT_PATTERN, max_length=64)
    version: int | None = Field(default=None, ge=1, le=2147483647, strict=True)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    biotype: str | None = Field(default=None, min_length=1, max_length=128)
    assembly_name: str = Field(min_length=1, max_length=128)
    sequence_region: str = Field(min_length=1, max_length=128)
    start_position: int = Field(ge=1, le=9223372036854775807, strict=True)
    end_position: int = Field(ge=1, le=9223372036854775807, strict=True)
    strand: Literal["+", "-"]

    @model_validator(mode="after")
    def valid_order(self) -> "NormalizedTranscript":
        if self.end_position < self.start_position:
            raise ValueError("Transcript coordinate order is invalid.")
        return self


class NormalizedTranscriptBatch(NormalizedModel):
    ensembl_gene_id: str = Field(pattern=ENSEMBL_GENE_PATTERN, max_length=64)
    taxonomy_id: str = Field(pattern=r"^[1-9][0-9]{0,15}$")
    source_release: str = Field(pattern=r"^[1-9][0-9]{0,5}$")
    retrieved_at: datetime
    transcripts: list[NormalizedTranscript] = Field(max_length=200)
