from typing import Literal

from pydantic import Field, HttpUrl, model_validator

from app.schemas.common import ApiModel, PatchModel, ProvenanceFields, StoredProvenanceFields
from app.schemas.organism import OrganismSummary


class ProteinSummary(ApiModel):
    id: int
    accession: str
    name: str


class GeneBase(ProvenanceFields):
    symbol: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=512)
    description: str | None = None
    organism_id: int = Field(gt=0)
    chromosome: str | None = Field(default=None, max_length=64)
    start_position: int | None = Field(default=None, ge=0)
    end_position: int | None = Field(default=None, ge=0)
    strand: Literal["+", "-"] | None = None
    ncbi_gene_id: str | None = Field(default=None, min_length=1, max_length=64)
    ensembl_gene_id: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_position_order(self) -> "GeneBase":
        if (
            self.start_position is not None
            and self.end_position is not None
            and self.end_position < self.start_position
        ):
            raise ValueError("end_position must be greater than or equal to start_position")
        return self


class GeneCreate(GeneBase):
    pass


class GeneUpdate(PatchModel):
    non_nullable_fields = frozenset({"symbol", "name", "organism_id", "source"})

    symbol: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    organism_id: int | None = Field(default=None, gt=0)
    chromosome: str | None = Field(default=None, max_length=64)
    start_position: int | None = Field(default=None, ge=0)
    end_position: int | None = Field(default=None, ge=0)
    strand: Literal["+", "-"] | None = None
    ncbi_gene_id: str | None = Field(default=None, min_length=1, max_length=64)
    ensembl_gene_id: str | None = Field(default=None, min_length=1, max_length=64)
    source: str | None = Field(default=None, min_length=1, max_length=64)
    source_identifier: str | None = Field(default=None, max_length=255)
    source_url: HttpUrl | None = None


class GeneRead(GeneBase, StoredProvenanceFields):
    organism: OrganismSummary


class GeneDetail(GeneRead):
    proteins: list[ProteinSummary]
