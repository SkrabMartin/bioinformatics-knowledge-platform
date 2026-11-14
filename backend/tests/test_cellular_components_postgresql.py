import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tests.test_cellular_components import (
    test_cellular_component_browsing_search_and_aspect_separation as verify_search,
)
from tests.test_cellular_components import (
    test_cross_aspect_cycles_duplicates_and_invalid_targets_fail_closed as verify_guards,
)
from tests.test_cellular_components import (
    test_source_assertions_and_hierarchy_are_exposed_in_both_directions_and_graph as verify_graph,
)


@pytest.mark.parametrize("verify", [verify_search, verify_guards, verify_graph])
def test_postgresql_component_search_relationships_and_constraints(verify) -> None:
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
