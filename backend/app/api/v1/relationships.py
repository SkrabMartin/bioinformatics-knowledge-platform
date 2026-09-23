from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import RelationshipServiceDependency
from app.schemas.common import ErrorResponse, Page
from app.schemas.relationship import (
    EntityType,
    GeneDiseaseCreate,
    ProteinInteractionCreate,
    RelationshipRead,
    VariantDiseaseCreate,
    VariantGeneCreate,
)

router = APIRouter(prefix="/relationships", tags=["relationships"])


@router.post(
    "/gene-disease",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_gene_disease(
    payload: GeneDiseaseCreate, service: RelationshipServiceDependency
) -> RelationshipRead:
    return service.create_gene_disease(payload)


@router.post(
    "/variant-gene",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_variant_gene(
    payload: VariantGeneCreate, service: RelationshipServiceDependency
) -> RelationshipRead:
    return service.create_variant_gene(payload)


@router.post(
    "/variant-disease",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_variant_disease(
    payload: VariantDiseaseCreate, service: RelationshipServiceDependency
) -> RelationshipRead:
    return service.create_variant_disease(payload)


@router.post(
    "/protein-interaction",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_protein_interaction(
    payload: ProteinInteractionCreate, service: RelationshipServiceDependency
) -> RelationshipRead:
    return service.create_protein_interaction(payload)


@router.get("/{entity_type}/{entity_id}", response_model=Page[RelationshipRead])
def list_relationships(
    entity_type: EntityType,
    entity_id: int,
    service: RelationshipServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[RelationshipRead]:
    return service.list_for(entity_type, entity_id, page=page, page_size=page_size)
