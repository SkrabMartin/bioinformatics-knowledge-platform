from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from app.schemas.common import ProvenanceFields, StoredProvenanceFields
from app.schemas.relationship import RelationshipProvenance

TermKind = Literal["biological_process", "molecular_function"]
KnowledgeKind = Literal["pathway", "biological_process", "molecular_function"]


class KnowledgeFields(ProvenanceFields):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)
    source_release: str = Field(min_length=1, max_length=128)
    source_identifier: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=100000)


class PathwayCreate(KnowledgeFields):
    organism_id: int | None = Field(default=None, gt=0, le=9223372036854775807)


class PathwayRead(PathwayCreate, StoredProvenanceFields):
    pass


class TermCreate(KnowledgeFields):
    kind: TermKind
    go_id: str = Field(pattern=r"^GO:[0-9]{7}$")


class TermRead(TermCreate, StoredProvenanceFields):
    pass


class AnnotationCreate(RelationshipProvenance):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    entity_id: int = Field(gt=0, le=9223372036854775807)
    source_release: str = Field(min_length=1, max_length=128)
    evidence_kind: Literal["curated", "structured_metadata"]
    evidence_code: str | None = Field(default=None, pattern=r"^[A-Z]{2,6}$")


class ParentCreate(RelationshipProvenance):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    parent_id: int = Field(gt=0, le=9223372036854775807)
    source_release: str = Field(min_length=1, max_length=128)

    @field_validator("source", "source_identifier")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Source fields cannot be blank.")
        return value
