import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.graph import EdgeIndex, GraphRepository
from app.schemas.graph import (
    GraphEdge,
    GraphLimits,
    GraphNode,
    GraphResponse,
    TruncationReason,
    node_key,
)
from app.schemas.relationship import EntityType, RelationshipType
from app.services.entities import GeneService
from app.services.errors import ApplicationError
from app.services.relationships import RelationshipService

MAX_SCANNED_EDGES = 1000


class GraphTimeoutError(ApplicationError):
    status_code = 503
    code = "graph_timeout"


class _BudgetExpired(Exception):
    pass


class GraphService:
    """Read-only bounded BFS over the existing typed relationship tables."""

    def __init__(self, session: Session, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.session = session
        self.clock = clock
        self.relationships = RelationshipService(session)
        self.repository = GraphRepository(session)

    def explore(
        self,
        entity_type: EntityType,
        entity_id: int | None,
        *,
        limits: GraphLimits,
        gene_symbol: str | None = None,
        taxonomy_id: str = "9606",
    ) -> GraphResponse:
        deadline = self.clock() + get_settings().graph_timeout_ms / 1000
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        reasons: set[TruncationReason] = set()
        scanned = 0
        root_id = ""
        connection: Connection | None = None

        def before_execute(
            _connection: Connection,
            cursor: Any,
            _statement: str,
            _parameters: Any,
            _context: Any,
            _executemany: bool,
        ) -> None:
            remaining_ms = int((deadline - self.clock()) * 1000)
            if remaining_ms <= 0:
                raise _BudgetExpired
            # Direct DBAPI execution avoids recursively invoking this SQLAlchemy listener.
            # Applies the remaining budget to EVERY hydration query, not just a whole batch.
            cursor.execute(
                "SELECT set_config('statement_timeout', %s, true)", (f"{remaining_ms}ms",)
            )

        try:
            self._checkpoint(deadline)
            if self.session.get_bind().dialect.name == "postgresql":
                connection = self.session.connection()
                event.listen(connection, "before_cursor_execute", before_execute)
            if gene_symbol is not None:
                entity_id = GeneService(self.session).get_by_symbol(gene_symbol, taxonomy_id).id
            assert entity_id is not None
            root = self.relationships.node_for(entity_type, entity_id)
            self._checkpoint(deadline)
            root_id = node_key(root.entity_type, root.entity_id)
            nodes[root_id] = GraphNode(**root.model_dump(), id=root_id, depth=0)
            # Root always remains visible, even when clients filter other node types.
            effective = (
                limits.model_copy(
                    update={"entity_types": sorted(set([*limits.entity_types, entity_type]))}
                )
                if limits.entity_types
                else limits
            )
            frontier = {entity_type: [entity_id]}
            seen: dict[RelationshipType, list[int]] = defaultdict(list)
            # One final bounded pass closes edges between already discovered boundary nodes.
            for depth in range(1, limits.depth + 2):
                if not frontier:
                    break
                self._checkpoint(deadline)
                remaining = MAX_SCANNED_EDGES - scanned
                if remaining <= 0:
                    reasons.add("scan_limit")
                    break
                within: dict[EntityType, list[int]] | None = None
                if depth > limits.depth:
                    within = defaultdict(list)
                    for existing in nodes.values():
                        within[existing.entity_type].append(existing.entity_id)
                candidates = self.repository.incident(
                    frontier, limits=effective, seen=seen, limit=remaining + 1, within=within
                )
                if len(candidates) > remaining:
                    reasons.add("scan_limit")
                    candidates = candidates[:remaining]
                scanned += len(candidates)
                reserved = set(nodes)
                selected: list[EdgeIndex] = []
                for candidate in candidates:
                    seen[candidate.kind].append(candidate.entity_id)
                    keys = {
                        node_key(candidate.subject_type, candidate.subject_id),
                        node_key(candidate.object_type, candidate.object_id),
                    }
                    if len(reserved | keys) > limits.max_nodes:
                        reasons.add("node_limit")
                        continue
                    if len(edges) + len(selected) >= limits.max_edges:
                        reasons.add("edge_limit")
                        break
                    reserved.update(keys)
                    selected.append(candidate)
                self._checkpoint(deadline)
                assertions = (
                    self.relationships.read_many([(row.kind, row.entity_id) for row in selected])
                    if selected
                    else []
                )
                self._checkpoint(deadline)
                indexes = {(row.kind, row.entity_id): row for row in selected}
                if len(assertions) != len(selected):
                    reasons.add("data_changed")
                next_frontier: dict[EntityType, list[int]] = defaultdict(list)
                for assertion in assertions:
                    row = indexes[(assertion.relationship_type, assertion.relationship_id)]
                    if (
                        assertion.subject.entity_type,
                        assertion.subject.entity_id,
                        assertion.object.entity_type,
                        assertion.object.entity_id,
                    ) != (row.subject_type, row.subject_id, row.object_type, row.object_id):
                        reasons.add("data_changed")
                        continue
                    source = node_key(assertion.subject.entity_type, assertion.subject.entity_id)
                    target = node_key(assertion.object.entity_type, assertion.object.entity_id)
                    for node in (assertion.subject, assertion.object):
                        key = node_key(node.entity_type, node.entity_id)
                        if key not in nodes:
                            nodes[key] = GraphNode(**node.model_dump(), id=key, depth=depth)
                            next_frontier[node.entity_type].append(node.entity_id)
                    edge_id = f"{assertion.relationship_type}:{assertion.relationship_id}"
                    edges[edge_id] = GraphEdge(
                        id=edge_id,
                        source_node=source,
                        target_node=target,
                        directed=assertion.relationship_type != "protein_interaction",
                        assertion=assertion,
                    )
                frontier = next_frontier
                if "scan_limit" in reasons or "edge_limit" in reasons:
                    break
        except (_BudgetExpired, DBAPIError) as exc:
            if isinstance(exc, DBAPIError):
                if getattr(exc.orig, "sqlstate", None) != "57014":
                    raise
                # Rollback may issue SQL (for example ROLLBACK TO SAVEPOINT).
                # It must remain possible after the query budget has expired.
                if connection is not None:
                    event.remove(connection, "before_cursor_execute", before_execute)
                    connection = None
                self.session.rollback()
            if not nodes:
                raise GraphTimeoutError(
                    "Graph lookup exceeded its time budget before loading the root; "
                    "retry with a smaller query."
                ) from exc
            reasons.add("time_budget")
        finally:
            if connection is not None:
                event.remove(connection, "before_cursor_execute", before_execute)
        return GraphResponse(
            root_id=root_id,
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            limits=limits,
            truncated=bool(reasons),
            truncation_reasons=sorted(reasons),
            scanned_edges=scanned,
        )

    def _checkpoint(self, deadline: float) -> None:
        remaining_ms = int((deadline - self.clock()) * 1000)
        if remaining_ms <= 0:
            raise _BudgetExpired
