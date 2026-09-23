from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import OrganismServiceDependency
from app.models import Organism
from app.schemas.common import ErrorResponse, Page
from app.schemas.organism import OrganismCreate, OrganismRead, OrganismUpdate

router = APIRouter(prefix="/organisms", tags=["organisms"])


@router.get("", response_model=Page[OrganismRead])
def list_organisms(
    service: OrganismServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[OrganismRead]:
    return service.list(page=page, page_size=page_size)


@router.post(
    "",
    response_model=OrganismRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
def create_organism(payload: OrganismCreate, service: OrganismServiceDependency) -> Organism:
    return service.create(payload)


@router.get(
    "/{organism_id}", response_model=OrganismRead, responses={404: {"model": ErrorResponse}}
)
def get_organism(organism_id: int, service: OrganismServiceDependency) -> Organism:
    return service.get(organism_id)


@router.patch(
    "/{organism_id}",
    response_model=OrganismRead,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def update_organism(
    organism_id: int,
    payload: OrganismUpdate,
    service: OrganismServiceDependency,
) -> Organism:
    return service.update(organism_id, payload)
