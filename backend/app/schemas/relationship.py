from datetime import datetime
from typing import Literal

from pydantic import Field, HttpUrl

from app.schemas.common import ApiModel

EntityType = Literal["gene", "protein", "variant", "disease", "publication"]
RelationshipType = Literal[
    "gene_disease",
    "variant_gene",
    "variant_disease",
    "protein_interaction",
    "gene_protein",
    "publication_gene",
    "publication_protein",
    "publication_disease",
]
Predicate = Literal[
    "associated_with", "located_in", "interacts_with", "encodes", "mentions", "discusses", "studies"
]


class RelationshipProvenance(ApiModel):
    source: str = Field(min_length=1, max_length=64)
    source_identifier: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl | None = None
    imported_at: datetime | None = None
    evidence_text: str | None = Field(default=None, max_length=5000)


class GeneDiseaseCreate(RelationshipProvenance):
    gene_id: int = Field(gt=0)
    disease_id: int = Field(gt=0)


class VariantGeneCreate(RelationshipProvenance):
    variant_id: int = Field(gt=0)
    gene_id: int = Field(gt=0)


class VariantDiseaseCreate(RelationshipProvenance):
    variant_id: int = Field(gt=0)
    disease_id: int = Field(gt=0)


class ProteinInteractionCreate(RelationshipProvenance):
    protein_a_id: int = Field(gt=0)
    protein_b_id: int = Field(gt=0)


class RelationshipNode(ApiModel):
    entity_type: EntityType
    entity_id: int
    label: str
    href: str


class RelationshipRead(ApiModel):
    relationship_type: RelationshipType
    relationship_id: int
    predicate: Predicate
    subject: RelationshipNode
    object: RelationshipNode
    source: str
    source_identifier: str | None
    source_url: str | None
    imported_at: datetime | None
    evidence_text: str | None
    evidence_kind: Literal["structured_metadata", "curated"] | None = None
    provenance_basis: Literal["relationship_assertion", "protein_record"]
    created_at: datetime
    updated_at: datetime
