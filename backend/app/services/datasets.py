from math import ceil

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetPublication
from app.models.publication import Publication
from app.schemas.common import Page
from app.schemas.dataset import DatasetCreate, DatasetRead, DatasetResolveResult
from app.services.entities import model_values
from app.services.errors import ConflictError, NotFoundError


class DatasetService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, identifier: int) -> Dataset:
        record = self.session.get(Dataset, identifier)
        if record is None:
            raise NotFoundError("Dataset was not found.")
        return record

    def by_accession(self, accession: str) -> Dataset:
        record = self.session.scalar(
            select(Dataset).where(Dataset.repository == "GEO", Dataset.accession == accession)
        )
        if record is None:
            raise NotFoundError("Dataset was not found.")
        return record

    def browse(self, page: int, page_size: int, query: str | None = None) -> Page[DatasetRead]:
        statement = select(Dataset)
        if query:
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(
                or_(
                    *[
                        field.ilike(f"%{escaped}%", escape="\\")
                        for field in (Dataset.accession, Dataset.title, Dataset.description)
                    ]
                )
            )
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        records = self.session.scalars(
            statement.order_by(Dataset.accession, Dataset.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return Page(
            items=[DatasetRead.model_validate(record) for record in records],
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size) if total else 0,
        )

    def resolve_publications(self, identifier: int) -> DatasetResolveResult:
        # Dataset lock serializes resolution with concurrent metadata refresh/resolution.
        record = self.session.scalar(
            select(Dataset)
            .where(Dataset.id == identifier)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if record is None:
            raise NotFoundError("Dataset was not found.")
        if record.repository != "GEO" or record.source != "NCBI GEO":
            raise ConflictError("Only NCBI GEO source metadata can resolve GEO citations.")
        publications = self.session.scalars(
            select(Publication)
            .where(Publication.pubmed_id.in_(record.publication_pmids))
            .order_by(Publication.id)
            .with_for_update()
        ).all()
        prior = set(
            self.session.scalars(
                select(DatasetPublication.publication_id).where(
                    DatasetPublication.dataset_id == identifier
                )
            )
        )
        created = existing = 0
        for publication in publications:
            if publication.id in prior:
                existing += 1
                continue
            self.session.add(
                DatasetPublication(
                    dataset_id=identifier,
                    publication_id=publication.id,
                    reported_pmid=publication.pubmed_id,
                    source=record.source,
                    source_identifier=record.accession,
                    source_url=record.source_url,
                    imported_at=record.imported_at,
                    source_record_date=record.source_updated_date,
                    evidence_kind="structured_metadata",
                    evidence_text=(
                        f"GEO Series {record.accession} explicitly reported PMID "
                        f"{publication.pubmed_id}. First observed source citation; "
                        "not a biological or clinical assertion."
                    ),
                )
            )
            created += 1
        found = {p.pubmed_id for p in publications}
        missing = [pmid for pmid in record.publication_pmids if pmid not in found]
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(
                "Dataset citation resolution conflicts with an existing record."
            ) from exc
        return DatasetResolveResult(
            dataset_id=identifier, created=created, existing=existing, missing_pmids=missing
        )

    def save(self, payload: DatasetCreate, *, refresh: bool = False) -> tuple[Dataset, str]:
        record = self.session.scalar(
            select(Dataset)
            .where(Dataset.repository == payload.repository, Dataset.accession == payload.accession)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if record is not None and not refresh:
            raise ConflictError("Dataset identity already exists.")
        values = model_values(payload)
        action = "created"
        if record is None:
            record = Dataset(**values)
            self.session.add(record)
        else:
            if record.source != payload.source:
                raise ConflictError(
                    "Dataset has another source; explicit source review is required."
                )
            if payload.source_updated_date < record.source_updated_date:
                raise ConflictError("GEO source date regressed; no stored metadata was replaced.")
            action = (
                "updated"
                if any(
                    getattr(record, key) != value
                    for key, value in values.items()
                    if key != "imported_at"
                )
                else "unchanged"
            )
            for key, value in values.items():
                setattr(record, key, value)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Dataset conflicts with an existing source identity.") from exc
        return record, action
