from pydantic import Field, HttpUrl

from app.schemas.common import ApiModel, PatchModel, ProvenanceFields, StoredProvenanceFields


class OrganismSummary(ApiModel):
    id: int
    scientific_name: str
    common_name: str | None
    taxonomy_id: str | None


class OrganismBase(ProvenanceFields):
    scientific_name: str = Field(min_length=1, max_length=255)
    common_name: str | None = Field(default=None, max_length=255)
    taxonomy_id: str | None = Field(default=None, min_length=1, max_length=32)


class OrganismCreate(OrganismBase):
    pass


class OrganismUpdate(PatchModel):
    non_nullable_fields = frozenset({"scientific_name", "source"})

    scientific_name: str | None = Field(default=None, min_length=1, max_length=255)
    common_name: str | None = Field(default=None, max_length=255)
    taxonomy_id: str | None = Field(default=None, min_length=1, max_length=32)
    source: str | None = Field(default=None, min_length=1, max_length=64)
    source_identifier: str | None = Field(default=None, max_length=255)
    source_url: HttpUrl | None = None


class OrganismRead(OrganismBase, StoredProvenanceFields):
    pass
