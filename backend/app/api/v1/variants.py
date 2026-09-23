from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import VariantServiceDependency
from app.models import Variant
from app.schemas.common import ErrorResponse, Page
from app.schemas.variant import VariantCreate, VariantRead, VariantUpdate

router = APIRouter(prefix="/variants", tags=["variants"])


@router.get("", response_model=Page[VariantRead])
def list_variants(
    service: VariantServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[VariantRead]:
    return service.list(page=page, page_size=page_size)


@router.post(
    "",
    response_model=VariantRead,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_variant(payload: VariantCreate, service: VariantServiceDependency) -> Variant:
    return service.create(payload)


@router.get("/by-rsid/{rsid}", response_model=VariantRead)
def get_variant_by_rsid(rsid: str, service: VariantServiceDependency) -> Variant:
    return service.get_by_rsid(rsid)


@router.get("/{variant_id}", response_model=VariantRead)
def get_variant(variant_id: int, service: VariantServiceDependency) -> Variant:
    return service.get(variant_id)


@router.patch("/{variant_id}", response_model=VariantRead)
def update_variant(
    variant_id: int, payload: VariantUpdate, service: VariantServiceDependency
) -> Variant:
    return service.update(variant_id, payload)
