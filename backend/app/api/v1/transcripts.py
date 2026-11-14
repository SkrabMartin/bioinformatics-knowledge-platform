from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession
from app.schemas.common import Page
from app.schemas.transcript import TranscriptRead
from app.services.transcripts import TranscriptService

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.get("", response_model=Page[TranscriptRead])
def list_transcripts(
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    gene_id: Annotated[int | None, Query(gt=0)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> Page[TranscriptRead]:
    return TranscriptService(session).browse(page, page_size, gene_id, q)


@router.get("/by-ensembl/{accession}", response_model=TranscriptRead)
def read_transcript(accession: str, session: DatabaseSession) -> object:
    return TranscriptService(session).get(accession)
