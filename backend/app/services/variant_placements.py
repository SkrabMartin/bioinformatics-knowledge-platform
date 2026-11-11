import hashlib
import json
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Organism, Variant
from app.models.variant_placement import VariantPlacement
from app.schemas.common import Page
from app.schemas.variant_placement import VariantPlacementCreate, VariantPlacementRead
from app.services.errors import ConflictError, NotFoundError


class VariantPlacementService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def parent(self, variant_id: int) -> Variant:
        variant = self.session.get(Variant, variant_id)
        if variant is None:
            raise NotFoundError("Variant was not found.")
        return variant

    def browse(self, variant_id: int, page: int, page_size: int) -> Page[VariantPlacementRead]:
        self.parent(variant_id)
        statement = select(VariantPlacement).where(VariantPlacement.variant_id == variant_id)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        records = self.session.scalars(
            statement.order_by(VariantPlacement.id).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return Page(
            items=[VariantPlacementRead.model_validate(record) for record in records],
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size) if total else 0,
        )

    def create(self, variant_id: int, payload: VariantPlacementCreate) -> VariantPlacement:
        variant = self.parent(variant_id)
        self.session.refresh(variant, with_for_update=True)
        taxonomy = self.session.scalar(
            select(Organism.taxonomy_id).where(Organism.id == variant.organism_id).with_for_update()
        )
        if taxonomy is None or taxonomy != payload.taxonomy_id:
            raise ConflictError("Placement taxonomy must match the stored variant organism.")
        values = payload.model_dump(mode="python")
        values["source_url"] = str(payload.source_url)
        identity = {
            key: values[key]
            for key in (
                "assembly_name",
                "assembly_accession",
                "sequence_accession",
                "taxonomy_id",
                "coordinate_system",
                "strand",
                "start_position",
                "end_position",
                "reference_allele",
                "alternate_allele",
            )
        }
        key = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        record = VariantPlacement(variant_id=variant_id, representation_key=key, **values)
        self.session.add(record)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("This sourced variant placement already exists.") from exc
        return record
