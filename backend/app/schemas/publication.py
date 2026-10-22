import re
from datetime import date
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.common import ApiModel, ProvenanceFields, StoredProvenanceFields
from app.schemas.relationship import RelationshipProvenance

PublicationSort = Literal["newest", "oldest", "relevance"]
EvidenceKind = Literal["structured_metadata", "curated"]


class PublicationFields(ProvenanceFields):
    pubmed_id: str | None = Field(default=None, pattern=r"^[1-9][0-9]{0,31}$")
    doi: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=1, max_length=20000)
    abstract: str | None = Field(default=None, max_length=500000)
    journal: str | None = Field(default=None, max_length=512)
    authors: list[str] = Field(default_factory=list, max_length=10000)
    publication_date: str | None = None
    publication_date_text: str | None = Field(default=None, max_length=255)

    @field_validator("doi", mode="before")
    @classmethod
    def normalize_doi(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I)
        if not re.fullmatch(r"10\.[0-9]{4,9}/\S+", value, flags=re.I):
            raise ValueError("Invalid DOI format.")
        return value.lower()

    @field_validator("title")
    @classmethod
    def require_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Publication title cannot be blank.")
        return value.strip()

    @field_validator("publication_date")
    @classmethod
    def validate_partial_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"[0-9]{4}(?:-[0-9]{2}(?:-[0-9]{2})?)?", value):
            raise ValueError("Use YYYY, YYYY-MM, or YYYY-MM-DD for publication date.")
        date.fromisoformat(value + {4: "-01-01", 7: "-01", 10: ""}[len(value)])
        return value

    @model_validator(mode="after")
    def require_identifier(self) -> "PublicationFields":
        if self.pubmed_id is None and self.doi is None:
            raise ValueError("A publication requires a PMID or DOI.")
        return self


class PublicationRead(PublicationFields, StoredProvenanceFields):
    pass


class PublicationLinkCreate(RelationshipProvenance):
    entity_id: int = Field(gt=0)
    evidence_kind: EvidenceKind


class PublicationImportResult(ApiModel):
    entity_type: Literal["publication"] = "publication"
    entity_id: int
    identifier: str
    action: Literal["created", "updated", "unchanged"]
    gene_links_created: int = 0
