from sqlalchemy import Select, select

from app.models import Disease
from app.repositories.base import Repository


class DiseaseRepository(Repository[Disease]):
    model = Disease

    def list_statement(self) -> Select[tuple[Disease]]:
        return select(Disease).order_by(Disease.name, Disease.id)

    def by_mondo_id(self, mondo_id: str) -> Disease | None:
        return self.session.scalar(select(Disease).where(Disease.mondo_id == mondo_id))
