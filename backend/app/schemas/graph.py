from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.relationship import (
    EntityType,
    RelationshipNode,
    RelationshipRead,
    RelationshipType,
)

TruncationReason = Literal["node_limit", "edge_limit", "scan_limit", "time_budget", "data_changed"]


class GraphNode(RelationshipNode):
    id: str
    depth: int = Field(ge=0)


class GraphEdge(ApiModel):
    id: str
    source_node: str
    target_node: str
    directed: bool
    assertion: RelationshipRead


class GraphLimits(ApiModel):
    depth: int = Field(default=1, ge=1, le=3)
    max_nodes: int = Field(default=60, ge=1, le=150)
    max_edges: int = Field(default=120, ge=1, le=300)
    entity_types: list[EntityType] = Field(default_factory=list)
    relationship_types: list[RelationshipType] = Field(default_factory=list)


class GraphResponse(ApiModel):
    root_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    limits: GraphLimits
    truncated: bool
    truncation_reasons: list[TruncationReason]
    scanned_edges: int


def node_key(entity_type: EntityType, entity_id: int) -> str:
    return f"{entity_type}:{entity_id}"
