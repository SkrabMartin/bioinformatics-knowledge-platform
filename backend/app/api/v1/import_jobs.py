from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DatabaseSession
from app.core.security import require_admin
from app.schemas.common import Page
from app.schemas.import_job import ImportJobCreate, ImportJobItemRead, ImportJobRead
from app.services.import_jobs import ImportJobService

router = APIRouter(
    prefix="/import-jobs", tags=["import jobs"], dependencies=[Depends(require_admin)]
)


@router.post("", response_model=ImportJobRead, status_code=201)
def create_job(payload: ImportJobCreate, session: DatabaseSession) -> ImportJobRead:
    return ImportJobService(session).create(payload)


@router.get("", response_model=Page[ImportJobRead])
def list_jobs(
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ImportJobRead]:
    return ImportJobService(session).browse(page, page_size)


@router.get("/{job_id}", response_model=ImportJobRead)
def read_job(job_id: UUID, session: DatabaseSession) -> ImportJobRead:
    return ImportJobService(session).read(str(job_id))


@router.get("/{job_id}/items", response_model=Page[ImportJobItemRead])
def list_items(
    job_id: UUID,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ImportJobItemRead]:
    return ImportJobService(session).items(str(job_id), page, page_size)


@router.post("/{job_id}/cancel", response_model=ImportJobRead)
def cancel_job(job_id: UUID, session: DatabaseSession) -> ImportJobRead:
    return ImportJobService(session).cancel(str(job_id))
