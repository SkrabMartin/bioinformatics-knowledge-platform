from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.database import Base


class Repository[ModelT: Base]:
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def list(self, *, page: int, page_size: int) -> tuple[Sequence[ModelT], int]:
        statement = self.list_statement().offset((page - 1) * page_size).limit(page_size)
        items = self.session.scalars(statement).unique().all()
        total = self.session.scalar(select(func.count()).select_from(self.model)) or 0
        return items, total

    def list_statement(self) -> Select[tuple[ModelT]]:
        return select(self.model).order_by(getattr(self.model, "id"))  # noqa: B009

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.flush()
        return entity
