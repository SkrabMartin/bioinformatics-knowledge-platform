import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tests.test_dataset_graph import (
    test_exact_pmid_resolution_graph_reverse_filters_and_bounds as verify_resolution,
)
from tests.test_dataset_graph import (
    test_observed_citation_preserved_after_source_metadata_withdrawal as verify_history,
)


@pytest.mark.parametrize("verify", [verify_resolution, verify_history])
def test_postgresql_dataset_citations_json_date_union_and_source_history(verify) -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                verify(session)
            transaction.rollback()
    finally:
        engine.dispose()
