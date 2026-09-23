from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.fixtures import load_development_fixtures
from app.models import Gene, Organism, Protein

FIXTURE_PATH = Path(__file__).parents[2] / "data" / "fixtures" / "phase1_demo.json"


def test_development_fixture_loader_is_idempotent(session: Session) -> None:
    first = load_development_fixtures(session, FIXTURE_PATH)
    second = load_development_fixtures(session, FIXTURE_PATH)

    assert first == {"organisms_created": 1, "genes_created": 2, "proteins_created": 2}
    assert second == {"organisms_created": 0, "genes_created": 0, "proteins_created": 0}
    assert session.scalar(select(func.count()).select_from(Organism)) == 1
    assert session.scalar(select(func.count()).select_from(Gene)) == 2
    assert session.scalar(select(func.count()).select_from(Protein)) == 2
    assert session.scalar(select(Gene.source).limit(1)) == "development_fixture"
