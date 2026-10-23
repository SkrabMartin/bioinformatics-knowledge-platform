from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import DatabaseSession
from app.core.security import require_admin
from app.schemas.common import Page
from app.schemas.ontology import (
    AnnotationCreate,
    ParentCreate,
    PathwayCreate,
    PathwayRead,
    TermCreate,
    TermKind,
    TermRead,
)
from app.schemas.relationship import RelationshipRead
from app.services.ontology import KnowledgeService

router = APIRouter(tags=["pathways and ontology"])
admin = [Depends(require_admin)]
EntityID = Annotated[int, Path(gt=0, le=9223372036854775807)]


@router.get("/pathways", response_model=Page[PathwayRead])
def pathways(
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> object:
    return KnowledgeService(session).browse("pathway", page=page, page_size=page_size, query=q)


@router.get("/pathways/{identifier}", response_model=PathwayRead)
def pathway(identifier: EntityID, session: DatabaseSession) -> object:
    return KnowledgeService(session).get("pathway", identifier)


@router.post("/pathways", response_model=PathwayRead, status_code=201, dependencies=admin)
def create_pathway(payload: PathwayCreate, session: DatabaseSession) -> object:
    return KnowledgeService(session).create_pathway(payload)


@router.post(
    "/pathways/{identifier}/genes",
    response_model=RelationshipRead,
    status_code=201,
    dependencies=admin,
)
def annotate_pathway(
    identifier: EntityID, payload: AnnotationCreate, session: DatabaseSession
) -> RelationshipRead:
    return KnowledgeService(session).annotate("pathway", identifier, payload)


@router.get("/ontology/{kind}", response_model=Page[TermRead])
def terms(
    kind: TermKind,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> object:
    return KnowledgeService(session).browse(kind, page=page, page_size=page_size, query=q)


@router.get("/ontology/{kind}/{identifier}", response_model=TermRead)
def term(kind: TermKind, identifier: EntityID, session: DatabaseSession) -> object:
    return KnowledgeService(session).get(kind, identifier)


@router.post("/ontology", response_model=TermRead, status_code=201, dependencies=admin)
def create_term(payload: TermCreate, session: DatabaseSession) -> object:
    return KnowledgeService(session).create_term(payload)


@router.post(
    "/ontology/{kind}/{identifier}/annotations",
    response_model=RelationshipRead,
    status_code=201,
    dependencies=admin,
)
def annotate_term(
    kind: TermKind, identifier: EntityID, payload: AnnotationCreate, session: DatabaseSession
) -> RelationshipRead:
    return KnowledgeService(session).annotate(kind, identifier, payload)


@router.post(
    "/ontology/{kind}/{identifier}/parents",
    response_model=RelationshipRead,
    status_code=201,
    dependencies=admin,
)
def add_parent(
    kind: TermKind, identifier: EntityID, payload: ParentCreate, session: DatabaseSession
) -> RelationshipRead:
    return KnowledgeService(session).add_parent(kind, identifier, payload)
