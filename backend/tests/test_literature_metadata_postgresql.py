import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tests.test_literature_metadata import (
    test_keyword_ingestion_search_unicode_and_refresh as verify_keywords,
)
from tests.test_literature_metadata import (
    test_variant_literature_assertions_are_source_backed_bidirectional_and_graphed as verify_links,
)


@pytest.mark.parametrize("verify", [verify_keywords, verify_links])
def test_postgresql_keyword_json_search_and_variant_links(verify) -> None:
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
