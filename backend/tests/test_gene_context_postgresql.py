"""Source context schema and correlated alias search against disposable PostgreSQL."""

import os

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Gene, GeneAlias, GeneGenomicLocation
from app.search import SearchService
from tests.test_gene_context import import_gene


def test_postgresql_alias_search_identity_constraints_and_pagination() -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set BKP_TEST_POSTGRES_URL to an isolated migrated PostgreSQL database.")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                gene_id = import_gene(session)
                gene = session.get(Gene, gene_id)
                assert gene is not None
                session.add(
                    Gene(
                        symbol="DEMO-ALIAS",
                        name="Synthetic canonical symbol, not evidence",
                        organism_id=gene.organism_id,
                        source="development_fixture",
                    )
                )
                session.commit()
                service = SearchService(session)
                result = service.search("DEMO-ALIAS", page=1, page_size=1)
                assert result.total == 2 and result.pages == 2
                assert result.items[0].primary_label == "DEMO-ALIAS"
                second = service.search("DEMO-ALIAS", page=2, page_size=1)
                assert second.items[0].entity_id == gene_id
                assert any(field.field == "alias" for field in second.items[0].matched_fields)
                assert service.search("%", page=1, page_size=20).total == 0
                assert session.scalar(select(func.count()).select_from(GeneGenomicLocation)) == 2
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.add(
                        GeneGenomicLocation(
                            gene_id=gene_id,
                            sequence_accession="DEMO_SEQ.INVALID",
                            start_position=0,
                            end_position=5,
                            strand="+",
                            source="development_fixture",
                            source_identifier="demo-invalid",
                        )
                    )
                    session.flush()
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.add(
                        GeneAlias(
                            gene_id=gene_id,
                            alias="DEMO-ALIAS",
                            source="NCBI Gene",
                            source_identifier="999999",
                        )
                    )
                    session.flush()
                assert service.search("DEMO-ALIAS", page=1, page_size=20).total == 2
            transaction.rollback()
    finally:
        engine.dispose()
