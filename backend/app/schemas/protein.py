from pydantic import Field, HttpUrl

from app.schemas.common import ApiModel, PatchModel, ProvenanceFields, StoredProvenanceFields
from app.schemas.organism import OrganismSummary


class GeneSummary(ApiModel):
    id: int
    symbol: str
    name: str


class ProteinBase(ProvenanceFields):
    accession: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=512)
    gene_id: int | None = Field(default=None, gt=0)
    organism_id: int = Field(gt=0)
    function: str | None = None
    sequence_length: int | None = Field(default=None, gt=0)


class ProteinCreate(ProteinBase):
    pass


class ProteinUpdate(PatchModel):
    non_nullable_fields = frozenset({"accession", "name", "organism_id", "source"})

    accession: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=512)
    gene_id: int | None = Field(default=None, gt=0)
    organism_id: int | None = Field(default=None, gt=0)
    function: str | None = None
    sequence_length: int | None = Field(default=None, gt=0)
    source: str | None = Field(default=None, min_length=1, max_length=64)
    source_identifier: str | None = Field(default=None, max_length=255)
    source_url: HttpUrl | None = None


class ProteinRead(ProteinBase, StoredProvenanceFields):
    organism: OrganismSummary
    gene: GeneSummary | None
