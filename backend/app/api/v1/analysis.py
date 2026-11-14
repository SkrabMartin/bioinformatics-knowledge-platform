from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession
from app.schemas.gene_overlap import GeneOverlapRead, OverlapNamespace
from app.services.gene_overlap import gene_overlap

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/gene-overlap", response_model=GeneOverlapRead)
def compare_gene_lists(
    session: DatabaseSession,
    left: Annotated[list[str], Query(min_length=1, max_length=50)],
    right: Annotated[list[str], Query(min_length=1, max_length=50)],
    taxonomy_id: Annotated[str, Query(pattern=r"^[1-9][0-9]{0,15}$")],
    namespace: OverlapNamespace = "symbol",
) -> GeneOverlapRead:
    return gene_overlap(session, left, right, namespace, taxonomy_id)
