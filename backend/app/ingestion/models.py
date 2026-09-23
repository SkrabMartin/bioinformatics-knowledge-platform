from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class NormalizedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceProvenance(NormalizedModel):
    source: Literal["NCBI Gene", "UniProt"]
    source_identifier: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl
    retrieved_at: datetime


class NormalizedOrganism(NormalizedModel):
    scientific_name: str = Field(min_length=1, max_length=255)
    common_name: str | None = Field(default=None, max_length=255)
    taxonomy_id: str = Field(min_length=1, max_length=32)
    provenance: SourceProvenance


class NormalizedGene(NormalizedModel):
    symbol: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=512)
    description: str | None = None
    organism: NormalizedOrganism
    chromosome: str | None = Field(default=None, max_length=64)
    start_position: int | None = Field(default=None, ge=1)
    end_position: int | None = Field(default=None, ge=1)
    strand: Literal["+", "-"] | None = None
    ncbi_gene_id: str = Field(min_length=1, max_length=64)
    ensembl_gene_id: str | None = Field(default=None, max_length=64)
    provenance: SourceProvenance


class NormalizedProtein(NormalizedModel):
    accession: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=512)
    function: str | None = None
    sequence_length: int | None = Field(default=None, gt=0)
    gene_symbol: str | None = Field(default=None, max_length=64)
    ncbi_gene_id: str | None = Field(default=None, max_length=64)
    organism: NormalizedOrganism
    provenance: SourceProvenance
