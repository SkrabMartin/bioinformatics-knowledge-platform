from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from app.models import Variant
from app.repositories.base import Repository


class VariantRepository(Repository[Variant]):
    model = Variant

    def get(self, entity_id: int) -> Variant | None:
        return self.session.scalar(
            select(Variant).where(Variant.id == entity_id).options(selectinload(Variant.organism))
        )

    def list_statement(self) -> Select[tuple[Variant]]:
        return select(Variant).options(selectinload(Variant.organism)).order_by(Variant.id)

    def by_rsid(self, rsid: str) -> Variant | None:
        return self.session.scalar(
            select(Variant).where(Variant.rsid == rsid).options(selectinload(Variant.organism))
        )
