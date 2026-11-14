from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from app.core.version import APP_VERSION
from app.schemas.common import ApiModel, Page
from app.schemas.transcript import TranscriptSummary

CoordinateSystem = Literal["one_based_closed", "zero_based_half_open"]


class IntervalQuery(ApiModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    taxonomy_id: str = Field(pattern=r"^[1-9][0-9]{0,15}$")
    assembly_name: str = Field(min_length=1, max_length=128)
    sequence_region: str = Field(min_length=1, max_length=128)
    start: int = Field(ge=0, le=1_000_000_000_000)
    end: int = Field(ge=1, le=1_000_000_000_000)
    coordinate_system: CoordinateSystem = "one_based_closed"
    strand: Literal["+", "-"] | None = None
    page: int = Field(default=1, ge=1, le=1_000_000)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def valid_interval(self) -> "IntervalQuery":
        start = self.start + (self.coordinate_system == "zero_based_half_open")
        if start < 1 or self.end < start:
            raise ValueError("Require a nonempty interval with valid coordinate boundaries.")
        if self.end - start + 1 > 10_000_000:
            raise ValueError("Interval length cannot exceed 10,000,000 reference bases.")
        return self

    @property
    def closed_start(self) -> int:
        return self.start + (self.coordinate_system == "zero_based_half_open")


class TranscriptOverlap(TranscriptSummary):
    gene_id: int
    gene_symbol: str
    gene_href: str
    transcript_href: str
    overlap_start: int
    overlap_end: int
    overlap_bases: int


class IntervalReport(ApiModel):
    method: Literal["local_transcript_span_overlap_v1"] = "local_transcript_span_overlap_v1"
    software_version: str = APP_VERSION
    observed_at: datetime
    query: IntervalQuery
    normalized_start: int
    normalized_end: int
    result_coordinate_system: Literal["one_based_closed"] = "one_based_closed"
    matches: Page[TranscriptOverlap]
    interpretation: str = (
        "Overlap of stored whole transcript spans on the exact organism, assembly and sequence "
        "region. Exons, introns and coding intervals are not distinguished. No sequence lookup, "
        "assembly equivalence, liftover, variant effect or biological association is inferred. "
        "Empty results reflect local coverage only. Counts and pages may change during concurrent "
        "imports; this is not an immutable genome snapshot."
    )
