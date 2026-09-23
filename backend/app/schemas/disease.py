from pydantic import Field, HttpUrl

from app.schemas.common import PatchModel, ProvenanceFields, StoredProvenanceFields


class DiseaseCreate(ProvenanceFields):
    name: str = Field(min_length=1, max_length=512)
    description: str | None = None
    mondo_id: str | None = Field(default=None, pattern=r"^MONDO:[0-9]+$", max_length=64)
    disease_ontology_id: str | None = Field(default=None, pattern=r"^DOID:[0-9]+$", max_length=64)


class DiseaseUpdate(PatchModel):
    non_nullable_fields = frozenset({"name", "source"})

    name: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    mondo_id: str | None = Field(default=None, pattern=r"^MONDO:[0-9]+$", max_length=64)
    disease_ontology_id: str | None = Field(default=None, pattern=r"^DOID:[0-9]+$", max_length=64)
    source: str | None = Field(default=None, min_length=1, max_length=64)
    source_identifier: str | None = Field(default=None, max_length=255)
    source_url: HttpUrl | None = None


class DiseaseRead(DiseaseCreate, StoredProvenanceFields):
    pass
