from pydantic import Field, HttpUrl, model_validator

from app.schemas.common import PatchModel, ProvenanceFields, StoredProvenanceFields
from app.schemas.organism import OrganismSummary


class VariantCreate(ProvenanceFields):
    rsid: str | None = Field(default=None, pattern=r"^rs[0-9]+$", max_length=64)
    hgvs: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    organism_id: int = Field(gt=0)

    @model_validator(mode="after")
    def require_identifier(self) -> "VariantCreate":
        if not self.rsid and not self.hgvs:
            raise ValueError("A variant requires an rsID or HGVS expression.")
        return self


class VariantUpdate(PatchModel):
    non_nullable_fields = frozenset({"organism_id", "source"})

    rsid: str | None = Field(default=None, pattern=r"^rs[0-9]+$", max_length=64)
    hgvs: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    organism_id: int | None = Field(default=None, gt=0)
    source: str | None = Field(default=None, min_length=1, max_length=64)
    source_identifier: str | None = Field(default=None, max_length=255)
    source_url: HttpUrl | None = None


class VariantRead(VariantCreate, StoredProvenanceFields):
    organism: OrganismSummary
