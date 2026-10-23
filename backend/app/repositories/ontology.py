from collections.abc import Sequence
from typing import cast

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import OntologyParent, OntologyTerm, Pathway
from app.schemas.ontology import KnowledgeKind


class KnowledgeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def browse(
        self, kind: KnowledgeKind, *, page: int, page_size: int, query: str | None
    ) -> tuple[Sequence[Pathway | OntologyTerm], int]:
        model: type[Pathway] | type[OntologyTerm] = Pathway if kind == "pathway" else OntologyTerm
        conditions = []
        if kind != "pathway":
            conditions.append(OntologyTerm.kind == kind)
        if query:
            # Escape SQL LIKE metacharacters; a query is literal text, not a wildcard expression.
            pattern = (
                "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            )
            identifier = Pathway.source_identifier if kind == "pathway" else OntologyTerm.go_id
            conditions.append(
                or_(model.name.ilike(pattern, escape="\\"), identifier.ilike(pattern, escape="\\"))
            )
        statement = select(model).where(*conditions)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        items = self.session.scalars(
            statement.order_by(model.name, model.id).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return cast(Sequence[Pathway | OntologyTerm], items), total

    def ancestors(self, term_id: int) -> list[int]:
        # UNION (not UNION ALL) deduplicates shared ancestors and terminates even on corrupt cycles.
        ancestors = (
            select(OntologyParent.parent_id.label("id"))
            .where(OntologyParent.child_id == term_id)
            .cte("ancestors", recursive=True)
        )
        ancestors = ancestors.union(
            select(OntologyParent.parent_id).join(
                ancestors, OntologyParent.child_id == ancestors.c.id
            )
        )
        return list(self.session.scalars(select(ancestors.c.id).limit(1001)))
