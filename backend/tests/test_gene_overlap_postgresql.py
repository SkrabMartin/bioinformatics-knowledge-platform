import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.gene_overlap import AnalysisTimeout, gene_overlap
from tests.test_gene_overlap import (
    test_overlap_dedup_coverage_provenance_and_exact_sets as verify_symbols,
)
from tests.test_gene_overlap import (
    test_overlap_registry_taxonomy_case_and_empty_union as verify_registry,
)


@pytest.mark.parametrize("verify", [verify_symbols, verify_registry])
def test_postgresql_overlap_identity_sets_and_source_dates(verify):
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                verify(session)
                session.rollback()
                assert session.scalar(text("SHOW statement_timeout")) == "0"
            transaction.rollback()
    finally:
        engine.dispose()


def test_postgresql_overlap_timeout_is_safe_and_transaction_local(monkeypatch):
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            original = session.execute

            def execute(statement, *args, **kwargs):
                if "FROM genes" in str(statement):
                    return original(text("SELECT pg_sleep(4)"))
                return original(statement, *args, **kwargs)

            monkeypatch.setattr(session, "execute", execute)
            with pytest.raises(AnalysisTimeout):
                gene_overlap(session, ["AAA"], ["AAA"], "symbol", "999991")
            session.rollback()
            assert session.scalar(text("SHOW statement_timeout")) == "0"
    finally:
        engine.dispose()
