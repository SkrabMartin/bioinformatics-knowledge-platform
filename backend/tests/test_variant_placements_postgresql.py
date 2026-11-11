import os

import pytest
from sqlalchemy import create_engine, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Variant, VariantPlacement
from app.schemas.organism import OrganismUpdate
from app.schemas.variant import VariantUpdate
from app.schemas.variant_placement import VariantPlacementCreate
from app.services.entities import OrganismService, VariantService
from app.services.errors import ConflictError
from app.services.variant_placements import VariantPlacementService
from tests.test_variant_placements import placement, seed


def test_postgresql_placement_bounds_uniqueness_and_parent_guards() -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                variant_id, organism_id = seed(session)
                service = VariantPlacementService(session)
                record = service.create(
                    variant_id, VariantPlacementCreate.model_validate(placement())
                )
                record_id = record.id
                with pytest.raises(ConflictError):
                    service.create(variant_id, VariantPlacementCreate.model_validate(placement()))
                service.create(
                    variant_id,
                    VariantPlacementCreate.model_validate(
                        placement()
                        | {
                            "reference_allele": "A" * 1000,
                            "alternate_allele": "C" * 1000,
                            "end_position": 1009,
                            "source_release": "TEST-2",
                        }
                    ),
                )
                assert service.browse(variant_id, 1, 10).total == 2
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.execute(
                        update(VariantPlacement)
                        .where(VariantPlacement.id == record_id)
                        .values(end_position=10)
                    )
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.execute(delete(Variant).where(Variant.id == variant_id))
                with pytest.raises(ConflictError):
                    VariantService(session).update(variant_id, VariantUpdate(rsid="rs123"))
                with pytest.raises(ConflictError):
                    OrganismService(session).update(organism_id, OrganismUpdate(taxonomy_id="123"))
            transaction.rollback()
    finally:
        engine.dispose()
