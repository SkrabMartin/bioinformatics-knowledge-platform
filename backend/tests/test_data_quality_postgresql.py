import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.ingestion.services import ProteinIngestionService
from app.models import Gene
from app.services.data_quality import DataQualityService
from tests.test_gene_identifiers import MappedProvider, seed


def test_postgresql_review_correlates_identity_and_retains_data() -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires isolated migrated PostgreSQL")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                gene_id = seed(session)
                ProteinIngestionService(session, MappedProvider()).import_protein("P04637")
                before = session.execute(select(Gene.id, Gene.ensembl_gene_id)).all()
                report = DataQualityService(session).report()
                findings = {item.code: item for item in report.checks}
                assert findings["identifier_projection"].affected == 0
                assert findings["identifier_evidence"].affected == 0
                assert findings["gene_ensembl_coverage"].affected == 0
                assert findings["gene_provenance"].assessed == 1
                assert session.get(Gene, gene_id) is not None
                assert session.execute(select(Gene.id, Gene.ensembl_gene_id)).all() == before
            transaction.rollback()
    finally:
        engine.dispose()
