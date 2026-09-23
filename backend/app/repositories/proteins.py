from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from app.models import Protein
from app.repositories.base import Repository


class ProteinRepository(Repository[Protein]):
    model = Protein

    def get(self, entity_id: int) -> Protein | None:
        statement = (
            select(Protein)
            .where(Protein.id == entity_id)
            .options(selectinload(Protein.organism), selectinload(Protein.gene))
        )
        return self.session.scalar(statement)

    def list_statement(self) -> Select[tuple[Protein]]:
        return (
            select(Protein)
            .options(selectinload(Protein.organism), selectinload(Protein.gene))
            .order_by(Protein.accession, Protein.id)
        )

    def by_accession(self, accession: str) -> Protein | None:
        return self.session.scalar(
            select(Protein)
            .where(Protein.accession == accession.upper())
            .options(selectinload(Protein.organism), selectinload(Protein.gene))
        )
