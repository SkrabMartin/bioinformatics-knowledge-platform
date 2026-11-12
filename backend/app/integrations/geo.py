"""Bounded, public GEO Series metadata only. Never fetch experimental files."""

import re
from collections import defaultdict
from datetime import UTC, date, datetime

from pydantic import ValidationError

from app.integrations.errors import UpstreamResponseError
from app.integrations.http import TextHttpClient
from app.schemas.dataset import DatasetCreate

MAX_SOFT_BYTES = 2_000_000
MONTHS = {
    name: index
    for index, name in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1
    )
}


class GeoSeriesAdapter:
    def __init__(self, http: TextHttpClient) -> None:
        self.http = http

    def fetch_dataset(self, accession: str) -> DatasetCreate:
        if not re.fullmatch(r"GSE[1-9][0-9]{0,15}", accession):
            raise ValueError("A valid GEO Series accession is required.")
        raw = self.http.get_text(
            "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi",
            params={"acc": accession, "targ": "self", "form": "text", "view": "brief"},
            not_found_message="GEO Series was not found.",
        )
        return parse_geo_series(raw, accession)


def parse_geo_series(raw: str, requested: str) -> DatasetCreate:
    def fail() -> UpstreamResponseError:
        return UpstreamResponseError(
            "NCBI GEO", "GEO returned unsupported or inconsistent series metadata."
        )

    if len(raw.encode("utf-8")) > MAX_SOFT_BYTES:
        raise fail()
    fields: dict[str, list[str]] = defaultdict(list)
    headers = []
    allowed = {
        "title",
        "geo_accession",
        "status",
        "summary",
        "type",
        "sample_id",
        "sample_organism",
        "sample_taxid",
        "platform_id",
        "pubmed_id",
        "last_update_date",
    }
    for line in raw.splitlines():
        if line.startswith("^"):
            headers.append(line.strip())
        if line.startswith("!Series_") and " = " in line:
            key, value = line.split(" = ", 1)
            key = key.removeprefix("!Series_")
            if key in allowed:
                fields[key].append(value.strip())
    if headers != [f"^SERIES = {requested}"] or fields["geo_accession"] != [requested]:
        raise fail()
    if len(fields["status"]) != 1 or not fields["status"][0].startswith("Public on "):
        raise fail()
    if len(fields["title"]) != 1 or len(fields["last_update_date"]) != 1:
        raise fail()
    samples = fields["sample_id"]
    if (
        len(samples) > 100000
        or len(samples) != len(set(samples))
        or any(not re.fullmatch(r"GSM[1-9][0-9]{0,15}", value) for value in samples)
    ):
        raise fail()
    try:
        month, day, year = fields["last_update_date"][0].split()
        updated = date(int(year), MONTHS[month], int(day))
        return DatasetCreate(
            repository="GEO",
            accession=requested,
            title=fields["title"][0],
            description="\n\n".join(fields["summary"]) or None,
            experiment_types=fields["type"],
            organism_names=fields["sample_organism"],
            taxonomy_ids=fields["sample_taxid"],
            platform_accessions=fields["platform_id"],
            publication_pmids=fields["pubmed_id"],
            sample_count=len(samples) if samples else None,
            source_updated_date=updated,
            source="NCBI GEO",
            source_identifier=requested,
            source_url=f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={requested}",
            imported_at=datetime.now(UTC),
        )
    except (ValueError, KeyError, ValidationError) as exc:
        raise fail() from exc
