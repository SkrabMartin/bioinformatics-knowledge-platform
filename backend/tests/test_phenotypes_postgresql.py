import os

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Disease, DiseasePhenotype, Phenotype
from app.schemas.phenotype import DiseasePhenotypeCreate, PhenotypeCreate
from app.schemas.search import SearchEntityType
from app.search import SearchService
from app.services.errors import ConflictError
from app.services.phenotypes import PhenotypeService
from tests.test_phenotypes import assertion, seed_disease, term


def test_postgresql_phenotype_constraints_search_and_signed_assertions() -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                service = PhenotypeService(session)
                disease_id = seed_disease(session)
                record = service.create(PhenotypeCreate.model_validate(term()))
                phenotype_id = record.id
                for qualifier in ["present", "excluded"]:
                    service.annotate(
                        disease_id,
                        DiseasePhenotypeCreate.model_validate(assertion(phenotype_id, qualifier)),
                    )
                with pytest.raises(ConflictError):
                    service.annotate(
                        disease_id, DiseasePhenotypeCreate.model_validate(assertion(phenotype_id))
                    )
                result = service.annotations(disease_id=disease_id, page=1, page_size=20)
                assert {item.qualifier for item in result.items} == {"present", "excluded"}
                assert result.total == 2
                search = SearchService(session).search(
                    "HP:0000001", page=1, page_size=20, entity_types=[SearchEntityType.PHENOTYPE]
                )
                assert search.total == 1 and search.items[0].href == f"/phenotype/{phenotype_id}"
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.execute(delete(Phenotype).where(Phenotype.id == phenotype_id))
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.execute(delete(Disease).where(Disease.id == disease_id))
                assert session.get(DiseasePhenotype, result.items[0].id) is not None
            transaction.rollback()
    finally:
        engine.dispose()
