from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import DatabaseSession
from app.schemas.graph import GraphLimits, GraphResponse
from app.schemas.relationship import EntityType, RelationshipType
from app.services.graph import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])
compatibility_router = APIRouter(prefix="/graph", tags=["graph"])


def graph_limits(
    depth: Annotated[int, Query(ge=1, le=3)] = 1,
    max_nodes: Annotated[int, Query(ge=1, le=150)] = 60,
    max_edges: Annotated[int, Query(ge=1, le=300)] = 120,
    entity_types: Annotated[list[EntityType] | None, Query(alias="type")] = None,
    relationship_types: Annotated[
        list[RelationshipType] | None, Query(alias="relationship_type")
    ] = None,
) -> GraphLimits:
    return GraphLimits(
        depth=depth,
        max_nodes=max_nodes,
        max_edges=max_edges,
        entity_types=entity_types or [],
        relationship_types=relationship_types or [],
    )


@router.get("/gene/by-symbol/{symbol}", response_model=GraphResponse)
@compatibility_router.get("/gene/{symbol}", response_model=GraphResponse, include_in_schema=False)
def graph_by_symbol(
    symbol: str,
    session: DatabaseSession,
    limits: Annotated[GraphLimits, Depends(graph_limits)],
    taxonomy_id: Annotated[str, Query(min_length=1, max_length=32)] = "9606",
) -> GraphResponse:
    return GraphService(session).explore(
        "gene", None, limits=limits, gene_symbol=symbol, taxonomy_id=taxonomy_id
    )


@router.get("/{entity_type}/{entity_id}", response_model=GraphResponse)
def graph_by_id(
    entity_type: EntityType,
    entity_id: Annotated[int, Path(gt=0, le=9223372036854775807)],
    session: DatabaseSession,
    limits: Annotated[GraphLimits, Depends(graph_limits)],
) -> GraphResponse:
    return GraphService(session).explore(entity_type, entity_id, limits=limits)
