from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import DatabaseSession
from app.core.security import require_admin
from app.schemas.common import Page
from app.schemas.variant_placement import VariantPlacementCreate, VariantPlacementRead
from app.services.variant_placements import VariantPlacementService

router = APIRouter(tags=["variant placements"])
EntityID = Annotated[int, Path(gt=0, le=9223372036854775807)]


@router.get("/variants/{identifier}/placements", response_model=Page[VariantPlacementRead])
def placements(
    identifier: EntityID,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> object:
    return VariantPlacementService(session).browse(identifier, page, page_size)


@router.post(
    "/variants/{identifier}/placements",
    response_model=VariantPlacementRead,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_placement(
    identifier: EntityID, payload: VariantPlacementCreate, session: DatabaseSession
) -> object:
    return VariantPlacementService(session).create(identifier, payload)
