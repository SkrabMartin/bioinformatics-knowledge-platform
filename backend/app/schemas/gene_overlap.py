from datetime import datetime
from typing import Literal

from pydantic import Field

from app.core.version import APP_VERSION
from app.schemas.common import ApiModel

OverlapNamespace = Literal["symbol", "ncbi_gene", "ensembl_gene"]


class OverlapGene(ApiModel):
    id: int
    symbol: str
    name: str
    href: str
    resolved_identifier: str
    identifier_record_id: int | None
    source: str
    source_identifier: str | None
    source_url: str | None
    imported_at: datetime | None
    updated_at: datetime


class OverlapInput(ApiModel):
    input_count: int
    unique_inputs: list[str]
    duplicates_removed: int
    unresolved: list[str]
    matched_inputs: dict[str, int]
    resolved_gene_count: int


class OverlapMetrics(ApiModel):
    left_size: int
    right_size: int
    intersection_size: int
    union_size: int
    jaccard: float | None = Field(ge=0, le=1)


class GeneOverlapRead(ApiModel):
    method: Literal["exact_local_gene_set_overlap_v1"] = "exact_local_gene_set_overlap_v1"
    software_version: str = APP_VERSION
    computed_at: datetime
    namespace: OverlapNamespace
    taxonomy_id: str
    coverage_complete: bool
    left: OverlapInput
    right: OverlapInput
    metrics: OverlapMetrics
    shared: list[OverlapGene]
    left_only: list[OverlapGene]
    right_only: list[OverlapGene]
    identity_policy: str = (
        "Symbols match the current case-sensitive symbol; NCBI/Ensembl match the canonical "
        "local identifier registry without version stripping. Full identifier evidence remains "
        "available on linked gene details; this report includes current gene provenance."
    )
    interpretation: str = (
        "Descriptive overlap of resolved local genes only. Unknown identifiers are excluded; "
        "an unresolved identifier does not establish biological absence. "
        "Jaccard = intersection / union; an empty union has no defined index. "
        "No enrichment, p-value, clinical inference or genome-wide coverage is implied. "
        "This is a current-record report, not an immutable source snapshot or saved analysis run."
    )
