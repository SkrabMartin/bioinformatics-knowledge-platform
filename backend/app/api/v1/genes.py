from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import GeneServiceDependency
from app.models import Gene
from app.schemas.common import ErrorResponse, Page
from app.schemas.gene import GeneCreate, GeneDetail, GeneRead, GeneUpdate

router = APIRouter(prefix="/genes", tags=["genes"])


@router.get("", response_model=Page[GeneRead])
def list_genes(
    service: GeneServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[GeneRead]:
    return service.list(page=page, page_size=page_size)


@router.post(
    "",
    response_model=GeneRead,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_gene(payload: GeneCreate, service: GeneServiceDependency) -> Gene:
    return service.create(payload)


@router.get(
    "/by-symbol/{symbol}",
    response_model=GeneDetail,
    responses={404: {"model": ErrorResponse}},
)
def get_gene_by_symbol(
    symbol: str,
    service: GeneServiceDependency,
    taxonomy_id: Annotated[str, Query(min_length=1, max_length=32)] = "9606",
) -> Gene:
    return service.get_by_symbol(symbol, taxonomy_id)


@router.get("/{gene_id}", response_model=GeneRead, responses={404: {"model": ErrorResponse}})
def get_gene(gene_id: int, service: GeneServiceDependency) -> Gene:
    return service.get(gene_id)


@router.patch(
    "/{gene_id}",
    response_model=GeneRead,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def update_gene(gene_id: int, payload: GeneUpdate, service: GeneServiceDependency) -> Gene:
    return service.update(gene_id, payload)
