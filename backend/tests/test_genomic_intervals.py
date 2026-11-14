import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Gene, Organism, Transcript
from app.schemas.genomic_interval import IntervalQuery
from app.services.genomic_intervals import GenomicIntervalService


def query(**updates):
    return IntervalQuery.model_validate(
        {
            "taxonomy_id": "999993",
            "assembly_name": "TESTv1",
            "sequence_region": "1",
            "start": 100,
            "end": 200,
            **updates,
        }
    )


def seed(session):
    org = Organism(
        scientific_name="Synthetic interval organism",
        taxonomy_id="999993",
        source="development_fixture",
    )
    other = Organism(
        scientific_name="Other synthetic interval organism",
        taxonomy_id="999994",
        source="development_fixture",
    )
    session.add_all([org, other])
    session.flush()
    gene = Gene(
        symbol="DEMO",
        name="Synthetic interval gene",
        organism_id=org.id,
        source="development_fixture",
    )
    other_gene = Gene(
        symbol="DEMO",
        name="Other synthetic interval gene",
        organism_id=other.id,
        source="development_fixture",
    )
    session.add_all([gene, other_gene])
    session.flush()
    for index, (start, end, strand, assembly, region, parent) in enumerate(
        [
            (1, 100, "+", "TESTv1", "1", gene.id),
            (200, 250, "-", "TESTv1", "1", gene.id),
            (201, 300, "+", "TESTv1", "1", gene.id),
            (100, 200, "+", "TESTv2", "1", gene.id),
            (100, 200, "+", "TESTv1", "chr1", gene.id),
            (100, 200, "+", "TESTv1", "1", other_gene.id),
        ],
        1,
    ):
        session.add(
            Transcript(
                gene_id=parent,
                ensembl_transcript_id=f"ENST{index:011d}",
                version=1,
                assembly_name=assembly,
                sequence_region=region,
                start_position=start,
                end_position=end,
                strand=strand,
                source="Ensembl",
                source_release="test",
                source_identifier=f"test-{index}",
                source_url="https://example.test/transcript",
            )
        )
    session.commit()


def test_interval_boundaries_coordinate_conversion_and_scope(session: Session):
    seed(session)
    service = GenomicIntervalService(session)
    origin = service.browse(query(start=0, end=1, coordinate_system="zero_based_half_open"))
    assert origin.matches.total == 1 and origin.matches.items[0].overlap_bases == 1
    before = session.scalar(select(func.count()).select_from(Transcript))
    closed = service.browse(query())
    assert closed.matches.total == 2
    assert [r.overlap_bases for r in closed.matches.items] == [1, 1]
    assert [(r.overlap_start, r.overlap_end) for r in closed.matches.items] == [
        (100, 100),
        (200, 200),
    ]
    half = service.browse(query(start=99, end=200, coordinate_system="zero_based_half_open"))
    assert half.normalized_start == 100 and half.normalized_end == 200
    assert [r.id for r in half.matches.items] == [r.id for r in closed.matches.items]
    assert (
        service.browse(
            query(start=100, end=200, coordinate_system="zero_based_half_open")
        ).matches.total
        == 1
    )
    reverse = service.browse(query(strand="-"))
    assert reverse.matches.total == 1 and reverse.matches.items[0].strand == "-"
    assert service.browse(query(assembly_name="unknown")).matches.total == 0
    assert service.browse(query(sequence_region="%")).matches.total == 0
    assert service.browse(query(sequence_region="chr1")).matches.total == 1
    assert service.browse(query(taxonomy_id="999994")).matches.total == 1
    first = closed.matches.items[0]
    assert first.source == "Ensembl" and first.source_release == "test"
    assert first.gene_href.endswith("taxonomy_id=999993") and first.transcript_href.startswith(
        "/transcript/"
    )
    assert session.scalar(select(func.count()).select_from(Transcript)) == before


def test_interval_pagination_stable_and_empty_windows(session: Session):
    seed(session)
    service = GenomicIntervalService(session)
    first = service.browse(query(page_size=1))
    second = service.browse(query(page=2, page_size=1))
    assert first.matches.total == second.matches.total == 2 and first.matches.pages == 2
    assert first.matches.items[0].id != second.matches.items[0].id
    assert service.browse(query(start=101, end=199)).matches.total == 0
    assert service.browse(query(page=3, page_size=1)).matches.items == []


@pytest.mark.parametrize(
    "updates",
    [
        {"start": 0},
        {"start": 201},
        {"start": 0, "end": 0, "coordinate_system": "zero_based_half_open"},
        {"start": 100, "end": 100, "coordinate_system": "zero_based_half_open"},
        {"end": 10_000_100},
        {"end": 1_000_000_000_001},
        {"strand": "?"},
        {"assembly_name": "  "},
        {"sequence_region": ""},
        {"page_size": 101},
    ],
)
def test_interval_rejects_invalid_or_empty_ranges(updates):
    with pytest.raises(ValidationError):
        query(**updates)


def test_interval_api_flat_query_validation_and_read_only(client: TestClient, session: Session):
    seed(session)
    path = "/api/v1/genomics/transcript-overlaps"
    params = {
        "taxonomy_id": "999993",
        "assembly_name": "TESTv1",
        "sequence_region": "1",
        "start": 100,
        "end": 200,
        "page_size": 1,
    }
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["matches"]["total"] == 2 and len(data["matches"]["items"]) == 1
    assert data["result_coordinate_system"] == "one_based_closed"
    assert client.get(path, params=params | {"start": 0}).status_code == 422
    assert (
        client.get(
            path, params=params | {"coordinate_system": "zero_based_half_open", "start": 99}
        ).status_code
        == 200
    )
    assert client.get(path).status_code == 422
    assert client.post(path, json=params).status_code == 405
