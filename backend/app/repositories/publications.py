from collections.abc import Sequence

from sqlalchemy import func, select

from app.models import Publication, PublicationGene
from app.repositories.base import Repository
from app.schemas.publication import PublicationSort
from app.search.publications import publication_match


class PublicationRepository(Repository[Publication]):
    model = Publication

    def page(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None,
        sort: PublicationSort,
        gene_id: int | None,
    ) -> tuple[Sequence[Publication], int]:
        statement = select(Publication)
        if gene_id is not None:
            # EXISTS avoids duplicate publications when multiple sources link the same gene.
            statement = statement.where(
                select(PublicationGene.id)
                .where(
                    PublicationGene.publication_id == Publication.id,
                    PublicationGene.gene_id == gene_id,
                )
                .exists()
            )
        rank = None
        if query is not None:
            condition, rank = publication_match(
                query, postgresql=self.session.get_bind().dialect.name == "postgresql"
            )
            statement = statement.where(condition)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        date_order = (
            Publication.publication_date.asc()
            if sort == "oldest"
            else Publication.publication_date.desc()
        )
        if sort == "relevance" and rank is not None:
            statement = statement.order_by(rank.desc())
        statement = statement.order_by(date_order.nullslast(), Publication.id)
        return self.session.scalars(
            statement.offset((page - 1) * page_size).limit(page_size)
        ).all(), total
