from fastapi import APIRouter

from app.api.dependencies import DatabaseSession
from app.schemas.import_status import ImportStatusRead
from app.services.import_status import import_status

router = APIRouter(prefix="/import-status", tags=["import status"])


@router.get("", response_model=ImportStatusRead)
def read_import_status(session: DatabaseSession) -> ImportStatusRead:
    return import_status(session)
