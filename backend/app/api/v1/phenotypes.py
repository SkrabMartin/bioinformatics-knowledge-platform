from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import DatabaseSession
from app.core.security import require_admin
from app.schemas.common import Page
from app.schemas.phenotype import (
    DiseasePhenotypeCreate,
    DiseasePhenotypeRead,
    PhenotypeCreate,
    PhenotypeRead,
)
from app.services.phenotypes import PhenotypeService

router = APIRouter(tags=["phenotypes"])
EntityID = Annotated[int, Path(gt=0, le=9223372036854775807)]
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.get("/phenotypes", response_model=Page[PhenotypeRead])
def browse(
    session: DatabaseSession,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> object:
    return PhenotypeService(session).browse(page, page_size, q)


@router.get("/phenotypes/{identifier}", response_model=PhenotypeRead)
def detail(identifier: EntityID, session: DatabaseSession) -> object:
    return PhenotypeService(session).get(identifier)


@router.post(
    "/phenotypes",
    response_model=PhenotypeRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create(payload: PhenotypeCreate, session: DatabaseSession) -> object:
    return PhenotypeService(session).create(payload)


@router.get("/diseases/{identifier}/phenotypes", response_model=Page[DiseasePhenotypeRead])
def disease_annotations(
    identifier: EntityID, session: DatabaseSession, page: PageNumber = 1, page_size: PageSize = 20
) -> object:
    return PhenotypeService(session).annotations(
        disease_id=identifier, page=page, page_size=page_size
    )


@router.get("/phenotypes/{identifier}/diseases", response_model=Page[DiseasePhenotypeRead])
def phenotype_annotations(
    identifier: EntityID, session: DatabaseSession, page: PageNumber = 1, page_size: PageSize = 20
) -> object:
    return PhenotypeService(session).annotations(
        phenotype_id=identifier, page=page, page_size=page_size
    )


@router.post(
    "/diseases/{identifier}/phenotypes",
    response_model=DiseasePhenotypeRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def annotate(
    identifier: EntityID, payload: DiseasePhenotypeCreate, session: DatabaseSession
) -> object:
    return PhenotypeService(session).annotate(identifier, payload)
