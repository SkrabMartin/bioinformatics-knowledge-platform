from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import DatabaseSession
from app.core.security import require_admin
from app.schemas.common import Page
from app.schemas.dataset import DatasetCreate, DatasetRead
from app.services.datasets import DatasetService

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=Page[DatasetRead])
def browse(
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> object:
    return DatasetService(session).browse(page, page_size, q)


@router.get("/by-accession/{accession}", response_model=DatasetRead)
def by_accession(
    accession: Annotated[str, Path(pattern=r"^GSE[1-9][0-9]{0,15}$")], session: DatabaseSession
) -> object:
    return DatasetService(session).by_accession(accession)


@router.get("/{identifier}", response_model=DatasetRead)
def detail(
    identifier: Annotated[int, Path(gt=0, le=9223372036854775807)], session: DatabaseSession
) -> object:
    return DatasetService(session).get(identifier)


@router.post("", response_model=DatasetRead, status_code=201, dependencies=[Depends(require_admin)])
def create(payload: DatasetCreate, session: DatabaseSession) -> object:
    return DatasetService(session).save(payload)[0]
