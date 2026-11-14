from math import ceil

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Disease
from app.models.phenotype import DiseasePhenotype, Phenotype
from app.schemas.common import Page
from app.schemas.phenotype import (
    DiseasePhenotypeCreate,
    DiseasePhenotypeRead,
    PhenotypeCreate,
    PhenotypeRead,
)
from app.services.errors import ConflictError, NotFoundError


class PhenotypeService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, identifier: int) -> Phenotype:
        record = self.session.get(Phenotype, identifier)
        if record is None:
            raise NotFoundError("Phenotype was not found.")
        return record

    def browse(self, page: int, page_size: int, query: str | None = None) -> Page[PhenotypeRead]:
        statement = select(Phenotype)
        if query:
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            statement = statement.where(
                or_(
                    Phenotype.hpo_id.ilike(pattern, escape="\\"),
                    Phenotype.name.ilike(pattern, escape="\\"),
                )
            )
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = self.session.scalars(
            statement.order_by(Phenotype.hpo_id, Phenotype.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return Page(
            items=[PhenotypeRead.model_validate(row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size) if total else 0,
        )

    def create(self, payload: PhenotypeCreate) -> Phenotype:
        values = payload.model_dump(mode="python")
        values["source_url"] = str(payload.source_url)
        record = Phenotype(**values)
        self.session.add(record)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Phenotype identity conflicts with an existing record.") from exc
        return self.get(record.id)

    def annotate(self, disease_id: int, payload: DiseasePhenotypeCreate) -> DiseasePhenotype:
        if self.session.get(Disease, disease_id) is None:
            raise NotFoundError("Disease was not found.")
        self.get(payload.phenotype_id)
        values = payload.model_dump(mode="python")
        values["source_url"] = str(payload.source_url)
        record = DiseasePhenotype(disease_id=disease_id, **values)
        self.session.add(record)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("This sourced disease/phenotype assertion already exists.") from exc
        return record

    def annotations(
        self,
        *,
        page: int,
        page_size: int,
        disease_id: int | None = None,
        phenotype_id: int | None = None,
    ) -> Page[DiseasePhenotypeRead]:
        if disease_id is not None and self.session.get(Disease, disease_id) is None:
            raise NotFoundError("Disease was not found.")
        if phenotype_id is not None:
            self.get(phenotype_id)
        statement = select(DiseasePhenotype)
        if disease_id is not None:
            statement = statement.where(DiseasePhenotype.disease_id == disease_id)
        if phenotype_id is not None:
            statement = statement.where(DiseasePhenotype.phenotype_id == phenotype_id)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = self.session.scalars(
            statement.options(
                selectinload(DiseasePhenotype.phenotype), selectinload(DiseasePhenotype.disease)
            )
            .order_by(DiseasePhenotype.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return Page(
            items=[DiseasePhenotypeRead.model_validate(row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size) if total else 0,
        )
