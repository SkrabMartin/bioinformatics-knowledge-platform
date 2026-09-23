from sqlalchemy import select

from app.models import Organism
from app.repositories.base import Repository


class OrganismRepository(Repository[Organism]):
    model = Organism

    def by_taxonomy_id(self, taxonomy_id: str) -> Organism | None:
        return self.session.scalar(select(Organism).where(Organism.taxonomy_id == taxonomy_id))
