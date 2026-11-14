import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.schemas.search import SearchEntityType
from app.search import SearchService
from tests.test_search_catalogues import (
    test_identifiers_versions_and_link_targets as verify_identifiers,
)
from tests.test_search_catalogues import (
    test_literal_wildcards_and_multi_term_matching as verify_literals,
)
from tests.test_search_catalogues import (
    test_related_parent_ranking_filters_and_suggestions as verify_ranking,
)
from tests.test_search_catalogues import (
    test_six_catalogues_join_shared_search_without_duplicates_or_kind_leaks as verify_categories,
)


@pytest.mark.parametrize(
    "verify", [verify_identifiers, verify_literals, verify_ranking, verify_categories]
)
def test_postgresql_catalogue_union_ranking_and_filters(verify) -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                verify(session)
                response = SearchService(session).search(
                    "shared",
                    page=1,
                    page_size=2,
                    entity_types=[SearchEntityType.TRANSCRIPT, SearchEntityType.PATHWAY],
                )
                assert response.total == 2 and response.counts.total == 6
                assert len(response.items) == 2
            transaction.rollback()
    finally:
        engine.dispose()
