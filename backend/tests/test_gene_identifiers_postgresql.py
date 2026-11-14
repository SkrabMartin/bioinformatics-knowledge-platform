"""PostgreSQL identity uniqueness and restrictive evidence ownership."""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.services import ProteinIngestionService
from app.models import Gene, GeneExternalIdentifier
from app.repositories.genes import GeneRepository
from app.services.gene_identifiers import resolve_gene_identifier
from tests.test_gene_identifiers import ENSEMBL, MappedProvider, seed


def test_postgresql_identifier_assertions_resolution_and_uniqueness() -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set BKP_TEST_POSTGRES_URL to an isolated migrated PostgreSQL database.")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                gene_id = seed(session)
                ProteinIngestionService(session, MappedProvider()).import_protein("P04637")
                result = resolve_gene_identifier(
                    GeneRepository(session), "ensembl_gene", ENSEMBL + ".20"
                )
                assert result.id == gene_id and len(result.external_identifiers) == 2
                assert sum(len(x.evidence) for x in result.external_identifiers) == 3
                other = Gene(
                    symbol="DEMO-OTHER",
                    name="Synthetic",
                    organism_id=result.organism_id,
                    source="development_fixture",
                )
                session.add(other)
                session.flush()
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.add(
                        GeneExternalIdentifier(
                            gene_id=other.id, namespace="ensembl_gene", accession=ENSEMBL
                        )
                    )
                    session.flush()
                assert (
                    resolve_gene_identifier(GeneRepository(session), "ncbi_gene", "7157").id
                    == gene_id
                )
            transaction.rollback()
    finally:
        engine.dispose()
