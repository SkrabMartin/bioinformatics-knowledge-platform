from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload

from app.models import Gene
from app.repositories.base import Repository


class GeneRepository(Repository[Gene]):
    model = Gene

    def get(self, entity_id: int) -> Gene | None:
        statement = (
            select(Gene)
            .where(Gene.id == entity_id)
            .options(selectinload(Gene.organism), selectinload(Gene.proteins))
        )
        return self.session.scalar(statement)

    def list_statement(self) -> Select[tuple[Gene]]:
        return select(Gene).options(selectinload(Gene.organism)).order_by(Gene.symbol, Gene.id)

    def by_external_identifier(self, identifier: str) -> Gene | None:
        return self.session.scalar(
            select(Gene).where(
                or_(Gene.ncbi_gene_id == identifier, Gene.ensembl_gene_id == identifier)
            )
        )

    def by_organism_and_symbol(self, organism_id: int, symbol: str) -> Gene | None:
        return self.session.scalar(
            select(Gene).where(Gene.organism_id == organism_id, Gene.symbol == symbol)
        )

    def by_symbol_and_taxonomy(self, symbol: str, taxonomy_id: str) -> Gene | None:
        return self.session.scalar(
            select(Gene)
            .join(Gene.organism)
            .where(
                func.upper(Gene.symbol) == symbol.upper(),
                Gene.organism.has(taxonomy_id=taxonomy_id),
            )
            .options(selectinload(Gene.organism), selectinload(Gene.proteins))
        )
