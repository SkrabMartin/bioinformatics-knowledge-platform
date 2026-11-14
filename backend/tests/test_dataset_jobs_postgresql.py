import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tests.test_dataset_jobs import (
    test_dataset_worker_import_replay_and_aggregate_privacy as verify_queue,
)


def test_postgresql_dataset_constraint_worker_json_aggregation():
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                verify_queue(session)
            transaction.rollback()
    finally:
        engine.dispose()
