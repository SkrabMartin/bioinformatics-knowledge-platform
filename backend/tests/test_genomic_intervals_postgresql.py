import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.genomic_intervals import GenomicIntervalService, IntervalTimeout
from tests.test_genomic_intervals import query
from tests.test_genomic_intervals import (
    test_interval_boundaries_coordinate_conversion_and_scope as verify_intervals,
)


def test_postgresql_interval_index_and_boundary_queries():
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                verify_intervals(session)
                session.rollback()
                assert session.scalar(text("SHOW statement_timeout")) == "0"
                session.execute(text("SET LOCAL enable_seqscan=off"))
                plan = session.execute(
                    text(
                        "EXPLAIN (FORMAT JSON) SELECT id FROM transcripts "
                        "WHERE assembly_name='TESTv1' AND sequence_region='1' "
                        "AND start_position<=200 AND end_position>=100"
                    )
                ).scalar_one()
                assert "ix_transcripts_interval" in str(plan)
                session.rollback()
            transaction.rollback()
    finally:
        engine.dispose()


def test_postgresql_interval_timeout_does_not_return_empty_matches(monkeypatch):
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            original = session.execute

            def execute(statement, *args, **kwargs):
                if "FROM transcripts" in str(statement):
                    return original(text("SELECT pg_sleep(4)"))
                return original(statement, *args, **kwargs)

            monkeypatch.setattr(session, "execute", execute)
            with pytest.raises(IntervalTimeout):
                GenomicIntervalService(session).browse(query())
            session.rollback()
            assert session.scalar(text("SHOW statement_timeout")) == "0"
    finally:
        engine.dispose()
