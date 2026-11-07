from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


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


class NormalizedGeneLocation(NormalizedModel):
    sequence_accession: str = Field(min_length=1, max_length=64)
    chromosome: str | None = Field(default=None, max_length=64)
    start_position: int = Field(ge=1)
    end_position: int = Field(ge=1)
    strand: Literal["+", "-"]

    @model_validator(mode="after")
    def validate_order(self) -> "NormalizedGeneLocation":
        if self.end_position < self.start_position:
            raise ValueError("end_position precedes start_position")
        return self


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
    aliases: list[str] = Field(default_factory=list, max_length=100)
    genomic_locations: list[NormalizedGeneLocation] = Field(default_factory=list, max_length=100)
    provenance: SourceProvenance

    @model_validator(mode="after")
    def validate_aliases(self) -> "NormalizedGene":
        aliases = list(dict.fromkeys(alias.strip() for alias in self.aliases))
        if any(not alias or len(alias) > 64 for alias in aliases):
            raise ValueError("Alias must contain 1-64 characters.")
        self.aliases = [alias for alias in aliases if alias != self.symbol]
        return self


class NormalizedProtein(NormalizedModel):
    accession: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=512)
    function: str | None = None
    sequence_length: int | None = Field(default=None, gt=0)
    gene_symbol: str | None = Field(default=None, max_length=64)
    ncbi_gene_id: str | None = Field(default=None, max_length=64)
    organism: NormalizedOrganism
    provenance: SourceProvenance
