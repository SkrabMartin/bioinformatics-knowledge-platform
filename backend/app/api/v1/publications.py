from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DatabaseSession
from app.core.security import require_admin
from app.schemas.common import Page
from app.schemas.publication import PublicationLinkCreate, PublicationRead, PublicationSort
from app.schemas.relationship import RelationshipRead
from app.services.publications import PublicationService

router = APIRouter(prefix="/publications", tags=["publications"])


@router.get("", response_model=Page[PublicationRead])
def list_publications(
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    sort: PublicationSort = "newest",
    gene_id: Annotated[int | None, Query(gt=0)] = None,
) -> Page[PublicationRead]:
    return PublicationService(session).browse(
        page=page, page_size=page_size, query=q, sort=sort, gene_id=gene_id
    )


@router.get("/{publication_id}", response_model=PublicationRead)
def get_publication(publication_id: int, session: DatabaseSession) -> object:
    return PublicationService(session).get(publication_id)


@router.post(
    "/{publication_id}/links/{entity_type}",
    response_model=RelationshipRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def link_publication(
    publication_id: int,
    entity_type: Literal["gene", "protein", "disease"],
    payload: PublicationLinkCreate,
    session: DatabaseSession,
) -> RelationshipRead:
    return PublicationService(session).link(publication_id, entity_type, payload)
