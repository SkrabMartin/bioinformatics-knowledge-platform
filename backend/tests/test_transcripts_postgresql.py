"""Transcript identity and coordinates on an explicitly disposable PostgreSQL."""

import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.transcripts import TranscriptIngestionService
from app.models import Transcript
from app.services.transcripts import TranscriptService
from tests.test_transcripts import GENE, TRANSCRIPT, provider, seed_gene


def test_postgresql_transcripts_constraints_roundtrip_and_replay() -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set BKP_TEST_POSTGRES_URL to an isolated migrated PostgreSQL database.")
    engine = create_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                gene = seed_gene(session)
                service = TranscriptIngestionService(session, provider())
                assert service.import_transcripts(GENE).created == 1
                assert service.import_transcripts(GENE).unchanged == 1
                record = TranscriptService(session).get(TRANSCRIPT)
                assert record.gene_id == gene.id and record.start_position == 200
                assert TranscriptService(session).browse(1, 1, gene.id, TRANSCRIPT).total == 1
                with pytest.raises(IntegrityError), session.begin_nested():
                    record.start_position = 0
                    session.flush()
                session.expire_all()
                assert session.scalar(select(Transcript.start_position)) == 200
            transaction.rollback()
    finally:
        engine.dispose()
