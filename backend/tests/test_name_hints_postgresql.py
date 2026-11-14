import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models import Gene, Organism, Protein, Publication
from app.search import SearchService
from app.search.names import name_hints
from app.search.service import SearchTimeout


def test_postgresql_indexed_name_hints_dedup_scope_and_transaction_settings():
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                org = Organism(
                    scientific_name="Synthetic human",
                    common_name="Synthetic human",
                    taxonomy_id="99999111",
                    source="development_fixture",
                )
                session.add(org)
                session.flush()
                gene = Gene(
                    symbol="DEMO1",
                    name="Mitochondrial quality regulator",
                    organism_id=org.id,
                    source="development_fixture",
                )
                protein = Protein(
                    accession="DEMO12",
                    name="Mitochondrial quality regulator protein",
                    organism_id=org.id,
                    source="development_fixture",
                )
                pub = Publication(
                    doi=f"10.1234/{uuid4().hex}",
                    title="Mitochondrial quality regulation in synthetic cells",
                    source="development_fixture",
                    authors=[],
                )
                session.add_all([gene, protein, pub])
                session.commit()
                session.execute(text("SELECT word_similarity('name','name')"))
                before = session.scalar(text("SHOW pg_trgm.word_similarity_threshold"))
                session.rollback()
                result = name_hints(session, "mitochodrial")
                assert {r.entity_type for r in result.items} == {"gene", "protein", "publication"}
                assert all(
                    r.similarity > result.threshold and r.source == "development_fixture"
                    for r in result.items
                )
                gene_hint = next(r for r in result.items if r.entity_type == "gene")
                assert (
                    gene_hint.href == f"/gene/DEMO1?taxonomy_id={org.taxonomy_id}"
                    and gene_hint.match_field == "name"
                )
                assert [
                    r.entity_type for r in name_hints(session, "mitochodrial", kind="protein").items
                ] == ["protein"]
                assert len(name_hints(session, "mitochodrial", limit=1).items) == 1
                organisms = name_hints(session, "synthetic humn", kind="organism").items
                assert len(organisms) == 1 and "type=organism" in organisms[0].href
                assert (
                    SearchService(session).search("mitochodrial", page=1, page_size=10).total == 0
                )
                session.rollback()
                assert session.scalar(text("SHOW pg_trgm.word_similarity_threshold")) == before
                assert session.scalar(text("SHOW statement_timeout")) == "0"
            transaction.rollback()
    finally:
        engine.dispose()


def test_postgresql_name_hints_cancel_slow_queries(monkeypatch):
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            original = session.execute

            def execute(statement, *args, **kwargs):
                if "UNION ALL" in str(statement):
                    return original(text("SELECT pg_sleep(4)"))
                return original(statement, *args, **kwargs)

            monkeypatch.setattr(session, "execute", execute)
            with pytest.raises(SearchTimeout):
                name_hints(session, "synthetic name")
            session.rollback()
            assert session.scalar(text("SHOW statement_timeout")) == "0"
    finally:
        engine.dispose()


def test_postgresql_word_similarity_has_existing_gin_index_path():
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            # Demonstrate index eligibility, not a production performance benchmark.
            connection.execute(text("SET LOCAL enable_seqscan = off"))
            plan = connection.execute(
                text(
                    "EXPLAIN (FORMAT JSON) SELECT id FROM organisms WHERE scientific_name %> :query"
                ),
                {"query": "Homo sapines"},
            ).scalar_one()
            assert "ix_organisms_scientific_name_trgm" in str(plan)
            transaction.rollback()
    finally:
        engine.dispose()
