from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import SearchServiceDependency
from app.schemas.common import ErrorResponse
from app.schemas.search import (
    SearchEntityType,
    SearchResponse,
    SearchSuggestionsResponse,
)

router = APIRouter(prefix="/search", tags=["search"])
compatibility_router = APIRouter(prefix="/search", tags=["search"])


@compatibility_router.get(
    "",
    response_model=SearchResponse,
    responses={422: {"model": ErrorResponse}},
    include_in_schema=False,
)
@router.get("", response_model=SearchResponse, responses={422: {"model": ErrorResponse}})
def search_entities(
    service: SearchServiceDependency,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    entity_types: Annotated[
        list[SearchEntityType] | None,
        Query(alias="type", description="Repeat to include multiple entity types."),
    ] = None,
) -> SearchResponse:
    return service.search(q, page=page, page_size=page_size, entity_types=entity_types)


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
def search_suggestions(
    service: SearchServiceDependency,
    q: Annotated[str, Query(min_length=2, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=12)] = 8,
) -> SearchSuggestionsResponse:
    return service.suggestions(q, limit=limit)
