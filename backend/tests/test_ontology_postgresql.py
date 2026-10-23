"""Real PostgreSQL checks against an opt-in disposable, migrated database."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import BiologicalProcess, Gene, GeneBiologicalProcess, MolecularFunction, Organism
from app.schemas.graph import GraphLimits
from app.schemas.ontology import ParentCreate
from app.services.errors import ConflictError
from app.services.graph import GraphService
from app.services.ontology import KnowledgeService


def test_postgresql_ontology_constraints_traversal_and_concurrent_hierarchy_lock() -> None:
    url = os.environ.get("BKP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set BKP_TEST_POSTGRES_URL to an isolated migrated PostgreSQL database.")
    engine = create_engine(url)
    provenance = {
        "source": "development_fixture",
        "source_identifier": uuid4().hex,
        "source_release": "test-only-v1",
    }
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                organism = Organism(
                    scientific_name="Synthetic PostgreSQL organism", source="development_fixture"
                )
                session.add(organism)
                session.flush()
                gene = Gene(
                    symbol=f"DEMO-{uuid4().hex[:8]}",
                    name="Synthetic test-only gene",
                    organism_id=organism.id,
                    source="development_fixture",
                )
                bp = BiologicalProcess(go_id="GO:9999981", name="Synthetic child", **provenance)
                parent = BiologicalProcess(
                    go_id="GO:9999982", name="Synthetic parent", **provenance
                )
                mf = MolecularFunction(go_id="GO:9999983", name="Synthetic function", **provenance)
                session.add_all([gene, bp, parent, mf])
                session.commit()
                service = KnowledgeService(session)
                with engine.connect() as competing, competing.begin() as competing_transaction:
                    competing.execute(text("SELECT pg_advisory_xact_lock(724017)"))
                    with pytest.raises(ConflictError, match="retry"):
                        service.add_parent(
                            "biological_process",
                            bp.id,
                            ParentCreate(parent_id=parent.id, **provenance),
                        )
                    competing_transaction.rollback()
                service.add_parent(
                    "biological_process", bp.id, ParentCreate(parent_id=parent.id, **provenance)
                )
                with pytest.raises(ConflictError, match="cycle"):
                    service.add_parent(
                        "biological_process", parent.id, ParentCreate(parent_id=bp.id, **provenance)
                    )
                graph = GraphService(session).explore(
                    "biological_process", bp.id, limits=GraphLimits()
                )
                assert len(graph.edges) == 1 and graph.edges[0].assertion.predicate == "is_a"
                # The composite FK rejects an MF term in a BP annotation outside API validation.
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.add(
                        GeneBiologicalProcess(
                            gene_id=gene.id,
                            term_id=mf.id,
                            kind="biological_process",
                            evidence_kind="curated",
                            **provenance,
                        )
                    )
                    session.flush()
            transaction.rollback()
    finally:
        engine.dispose()
