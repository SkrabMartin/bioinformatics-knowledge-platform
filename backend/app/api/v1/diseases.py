from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import DiseaseServiceDependency
from app.models import Disease
from app.schemas.common import ErrorResponse, Page
from app.schemas.disease import DiseaseCreate, DiseaseRead, DiseaseUpdate

router = APIRouter(prefix="/diseases", tags=["diseases"])


@router.get("", response_model=Page[DiseaseRead])
def list_diseases(
    service: DiseaseServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[DiseaseRead]:
    return service.list(page=page, page_size=page_size)


@router.post(
    "",
    response_model=DiseaseRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
def create_disease(payload: DiseaseCreate, service: DiseaseServiceDependency) -> Disease:
    return service.create(payload)


@router.get("/by-mondo/{mondo_id}", response_model=DiseaseRead)
def get_disease_by_mondo(mondo_id: str, service: DiseaseServiceDependency) -> Disease:
    return service.get_by_mondo_id(mondo_id)


@router.get("/{disease_id}", response_model=DiseaseRead)
def get_disease(disease_id: int, service: DiseaseServiceDependency) -> Disease:
    return service.get(disease_id)


@router.patch("/{disease_id}", response_model=DiseaseRead)
def update_disease(
    disease_id: int, payload: DiseaseUpdate, service: DiseaseServiceDependency
) -> Disease:
    return service.update(disease_id, payload)
