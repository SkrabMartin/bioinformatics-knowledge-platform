"""Graph runtime and actual query cancellation on a disposable PostgreSQL database."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Publication
from app.schemas.graph import GraphLimits
from app.services.graph import GraphService


def test_postgresql_graph_query_budget_and_transaction_local_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set BKP_TEST_POSTGRES_URL to an isolated migrated PostgreSQL database.")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                publication = Publication(
                    doi=f"10.1234/{uuid4().hex}",
                    title="Test-only graph root",
                    authors=[],
                    source="development_fixture",
                )
                session.add(publication)
                session.commit()
                root_id = publication.id
                # Real UNION over the existing eight typed relationship projections.
                graph = GraphService(session).explore("publication", root_id, limits=GraphLimits())
                assert len(graph.nodes) == 1 and not graph.edges and not graph.truncated
                session.rollback()
                assert session.scalar(text("SHOW statement_timeout")) == "0"
                monkeypatch.setattr(
                    "app.services.graph.get_settings",
                    lambda: Settings(_env_file=None, graph_timeout_ms=500),
                )
                service = GraphService(session)

                def slow_query(*args, **kwargs):
                    session.execute(text("SELECT pg_sleep(1)"))
                    return []

                monkeypatch.setattr(service.repository, "incident", slow_query)
                timed = service.explore("publication", root_id, limits=GraphLimits())
                assert len(timed.nodes) == 1
                assert timed.truncation_reasons == ["time_budget"]
                assert session.scalar(text("SHOW statement_timeout")) == "0"
            transaction.rollback()
    finally:
        engine.dispose()
