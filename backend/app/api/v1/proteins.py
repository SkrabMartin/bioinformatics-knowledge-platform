from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import ProteinServiceDependency
from app.models import Protein
from app.schemas.common import ErrorResponse, Page
from app.schemas.protein import ProteinCreate, ProteinRead, ProteinUpdate

router = APIRouter(prefix="/proteins", tags=["proteins"])


@router.get("", response_model=Page[ProteinRead])
def list_proteins(
    service: ProteinServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[ProteinRead]:
    return service.list(page=page, page_size=page_size)


@router.post(
    "",
    response_model=ProteinRead,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_protein(payload: ProteinCreate, service: ProteinServiceDependency) -> Protein:
    return service.create(payload)


@router.get(
    "/by-accession/{accession}",
    response_model=ProteinRead,
    responses={404: {"model": ErrorResponse}},
)
def get_protein_by_accession(accession: str, service: ProteinServiceDependency) -> Protein:
    return service.get_by_accession(accession)


@router.get("/{protein_id}", response_model=ProteinRead, responses={404: {"model": ErrorResponse}})
def get_protein(protein_id: int, service: ProteinServiceDependency) -> Protein:
    return service.get(protein_id)


@router.patch(
    "/{protein_id}",
    response_model=ProteinRead,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def update_protein(
    protein_id: int, payload: ProteinUpdate, service: ProteinServiceDependency
) -> Protein:
    return service.update(protein_id, payload)
