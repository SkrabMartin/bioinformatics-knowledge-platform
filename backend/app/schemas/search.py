from enum import StrEnum

from pydantic import Field

from app.schemas.common import ApiModel


class SearchEntityType(StrEnum):
    GENE = "gene"
    PROTEIN = "protein"
    ORGANISM = "organism"
    PUBLICATION = "publication"
    PHENOTYPE = "phenotype"
    TRANSCRIPT = "transcript"
    DISEASE = "disease"
    VARIANT = "variant"
    PATHWAY = "pathway"
    BIOLOGICAL_PROCESS = "biological_process"
    MOLECULAR_FUNCTION = "molecular_function"
    CELLULAR_COMPONENT = "cellular_component"


class SearchMatchedField(ApiModel):
    field: str
    value: str


class SearchOrganism(ApiModel):
    scientific_name: str
    taxonomy_id: str | None


class SearchResult(ApiModel):
    entity_type: SearchEntityType
    entity_id: int
    primary_label: str
    secondary_label: str | None
    description: str | None
    organism: SearchOrganism | None
    source: str
    href: str | None
    score: int = Field(ge=0)
    matched_fields: list[SearchMatchedField]


class SearchCounts(ApiModel):
    gene: int = Field(ge=0)
    protein: int = Field(ge=0)
    organism: int = Field(ge=0)
    publication: int = Field(default=0, ge=0)
    phenotype: int = Field(default=0, ge=0)
    transcript: int = Field(default=0, ge=0)
    disease: int = Field(default=0, ge=0)
    variant: int = Field(default=0, ge=0)
    pathway: int = Field(default=0, ge=0)
    biological_process: int = Field(default=0, ge=0)
    molecular_function: int = Field(default=0, ge=0)
    cellular_component: int = Field(default=0, ge=0)
    total: int = Field(ge=0)


class SearchResponse(ApiModel):
    query: str
    items: list[SearchResult]
    counts: SearchCounts
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class SearchSuggestion(ApiModel):
    entity_type: SearchEntityType
    value: str
    secondary_label: str | None
    href: str | None


class SearchSuggestionsResponse(ApiModel):
    query: str
    items: list[SearchSuggestion]
