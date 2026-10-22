from math import ceil
from typing import Literal

from sqlalchemy.orm import Session

from app.models import (
    Disease,
    Gene,
    Protein,
    Publication,
    PublicationDisease,
    PublicationGene,
    PublicationProtein,
)
from app.repositories.publications import PublicationRepository
from app.schemas.common import Page
from app.schemas.publication import PublicationLinkCreate, PublicationRead, PublicationSort
from app.schemas.relationship import RelationshipRead
from app.services.entities import EntityService, model_values
from app.services.errors import NotFoundError
from app.services.relationships import RelationshipService


class PublicationService(EntityService[Publication]):
    entity_name = "Publication"

    def __init__(self, session: Session) -> None:
        self.publications = PublicationRepository(session)
        super().__init__(session, self.publications)

    def browse(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None,
        sort: PublicationSort,
        gene_id: int | None,
    ) -> Page[PublicationRead]:
        if gene_id is not None and self.session.get(Gene, gene_id) is None:
            raise NotFoundError(f"Gene {gene_id} was not found.")
        items, total = self.publications.page(
            page=page, page_size=page_size, query=query, sort=sort, gene_id=gene_id
        )
        return Page(
            items=[PublicationRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )

    def link(
        self,
        publication_id: int,
        entity_type: Literal["gene", "protein", "disease"],
        data: PublicationLinkCreate,
    ) -> RelationshipRead:
        self.get(publication_id)
        model = {"gene": Gene, "protein": Protein, "disease": Disease}[entity_type]
        if self.session.get(model, data.entity_id) is None:
            raise NotFoundError(f"{entity_type} {data.entity_id} was not found.")
        values = model_values(data)
        values[f"{entity_type}_id"] = values.pop("entity_id")
        edge_models: dict[
            str, type[PublicationGene] | type[PublicationProtein] | type[PublicationDisease]
        ] = {
            "gene": PublicationGene,
            "protein": PublicationProtein,
            "disease": PublicationDisease,
        }
        edge_model = edge_models[entity_type]
        edge = edge_model(publication_id=publication_id, **values)
        return RelationshipService(self.session).create_publication_link(
            edge, f"publication_{entity_type}"
        )
