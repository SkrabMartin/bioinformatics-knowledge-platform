"""Opt-in tests against a separately migrated disposable PostgreSQL database."""

import os
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models import Publication
from app.repositories.publications import PublicationRepository
from app.schemas.search import SearchEntityType
from app.search import SearchService


def test_postgresql_migration_fulltext_and_partial_dates() -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set BKP_TEST_POSTGRES_URL to a disposable migrated PostgreSQL database.")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_indexes WHERE indexname IN "
                        "('ix_publications_search_document', 'ix_publications_title_trgm')"
                    )
                )
                == 2
            )
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                suffix = uuid4().hex
                citation = Publication(
                    doi=f"10.1234/{suffix}",
                    title=f"Synthetic {suffix} literature",
                    abstract="Test-only metadata, not scientific evidence.",
                    authors=[],
                    publication_date="2020",
                    source="development_fixture",
                )
                session.add(citation)
                session.flush()
                result = SearchService(session).search(
                    suffix, page=1, page_size=10, entity_types=[SearchEntityType.PUBLICATION]
                )
                assert result.total == 1
                assert result.items[0].href == f"/publication/{citation.id}"
                items, count = PublicationRepository(session).page(
                    page=1, page_size=10, query=suffix, sort="relevance", gene_id=None
                )
                assert count == 1
                assert items[0].publication_date == "2020"
                session.commit()
            transaction.rollback()
            assert not transaction.is_active
    finally:
        engine.dispose()
