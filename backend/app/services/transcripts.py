import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.models import Gene
from app.models.transcript import Transcript
from app.schemas.common import Page
from app.schemas.transcript import TranscriptRead
from app.services.errors import NotFoundError


class TranscriptService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, accession: str) -> Transcript:
        record = self.session.scalar(
            select(Transcript)
            .where(Transcript.ensembl_transcript_id == accession)
            .options(selectinload(Transcript.gene).selectinload(Gene.organism))
        )
        if record is None:
            raise NotFoundError("Transcript is not stored locally.")
        return record

    def browse(
        self, page: int, page_size: int, gene_id: int | None, query: str | None
    ) -> Page[TranscriptRead]:
        statement = select(Transcript).join(Gene)
        if gene_id is not None:
            statement = statement.where(Transcript.gene_id == gene_id)
        if query:
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            predicates: list[ColumnElement[bool]] = [
                field.ilike(f"%{escaped}%", escape="\\")
                for field in (Transcript.ensembl_transcript_id, Transcript.name, Gene.symbol)
            ]
            versioned = re.fullmatch(r"(ENS[A-Z]*T[0-9]{6,20})\.([1-9][0-9]{0,8})", query.strip())
            if versioned:
                predicates.append(
                    (Transcript.ensembl_transcript_id == versioned[1])
                    & (Transcript.version == int(versioned[2]))
                )
            statement = statement.where(or_(*predicates))
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        records = self.session.scalars(
            statement.options(selectinload(Transcript.gene).selectinload(Gene.organism))
            .order_by(Transcript.ensembl_transcript_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return Page(
            items=[TranscriptRead.model_validate(record) for record in records],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size,
        )
