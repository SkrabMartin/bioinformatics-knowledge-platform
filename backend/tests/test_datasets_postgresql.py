import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tests.test_datasets import (
    test_dataset_identity_refresh_regression_and_search as verify_dataset,
)


def test_postgresql_dataset_identity_json_dates_and_union_search() -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                verify_dataset(session)
            transaction.rollback()
    finally:
        engine.dispose()
