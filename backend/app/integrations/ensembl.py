"""Bounded explicit Ensembl gene-to-transcript annotations; no symbol identity inference."""

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from app.ingestion.transcript_models import (
    ENSEMBL_GENE_PATTERN,
    NormalizedTranscript,
    NormalizedTranscriptBatch,
)
from app.integrations.errors import UpstreamResponseError
from app.integrations.http import JsonHttpClient


class EnsemblTranscriptAdapter:
    def __init__(self, http: JsonHttpClient, *, base_url: str) -> None:
        self.http, self.base_url = http, base_url.rstrip("/")

    def fetch_transcripts(self, ensembl_gene_id: str) -> NormalizedTranscriptBatch:
        if not re.fullmatch(ENSEMBL_GENE_PATTERN, ensembl_gene_id):
            raise ValueError("A versionless Ensembl gene identifier is required.")
        gene = self.http.get_json(
            f"{self.base_url}/lookup/id/{ensembl_gene_id}",
            params={"expand": 1, "content-type": "application/json"},
            not_found_message="Ensembl gene was not found.",
        )
        species = gene.get("species")
        if (
            gene.get("id") != ensembl_gene_id
            or gene.get("object_type") != "Gene"
            or gene.get("db_type") != "core"
            or not isinstance(species, str)
            or not re.fullmatch(r"[a-z0-9_]{1,128}", species)
        ):
            raise UpstreamResponseError("Ensembl", "Gene lookup identity or species is invalid.")
        metadata = self.http.get_json(
            f"{self.base_url}/info/species",
            params={"content-type": "application/json"},
            not_found_message="Ensembl species metadata was not found.",
        )
        try:
            return self._normalize(gene, metadata)
        except (ValidationError, ValueError, KeyError, TypeError) as exc:
            raise UpstreamResponseError(
                "Ensembl", "Transcript annotations failed identity/context validation."
            ) from exc

    def _normalize(
        self, gene: dict[str, Any], metadata: dict[str, Any]
    ) -> NormalizedTranscriptBatch:
        species_rows = metadata.get("species")
        if not isinstance(species_rows, list) or len(species_rows) > 10000:
            raise ValueError("Invalid species metadata.")
        matches = [
            row
            for row in species_rows
            if isinstance(row, dict) and row.get("name") == gene["species"]
        ]
        if len(matches) != 1:
            raise ValueError("Species metadata is ambiguous.")
        species = matches[0]
        taxonomy, release = species.get("taxon_id"), species.get("release")
        if type(taxonomy) is not int or taxonomy < 1 or type(release) is not int or release < 1:
            raise ValueError("Explicit taxonomy and data release are required.")
        assembly = gene.get("assembly_name")
        if not isinstance(assembly, str) or not assembly or assembly != species.get("assembly"):
            raise ValueError("Assembly context does not agree.")
        start, end, strand = gene.get("start"), gene.get("end"), gene.get("strand")
        if (
            type(start) is not int
            or type(end) is not int
            or start < 1
            or end < start
            or type(strand) is not int
            or strand not in (-1, 1)
        ):
            raise ValueError("Invalid gene coordinates.")
        raw = gene.get("Transcript")
        if not isinstance(raw, list) or len(raw) > 200:
            raise ValueError("Missing or oversized transcript batch.")
        records = []
        seen: set[str] = set()
        for row in raw:
            if not isinstance(row, dict):
                raise ValueError("Invalid transcript response shape.")
            if (
                row.get("object_type") != "Transcript"
                or row.get("Parent") != gene["id"]
                or row.get("species") != gene["species"]
                or row.get("assembly_name") != assembly
                or row.get("seq_region_name") != gene.get("seq_region_name")
                or type(row.get("strand")) is not int
                or row["strand"] != strand
            ):
                raise ValueError("Transcript does not agree with its source gene.")
            record = NormalizedTranscript(
                ensembl_transcript_id=row["id"],
                version=row.get("version"),
                name=row.get("display_name"),
                biotype=row.get("biotype"),
                assembly_name=assembly,
                sequence_region=row["seq_region_name"],
                start_position=row["start"],
                end_position=row["end"],
                strand="+" if strand == 1 else "-",
            )
            if record.start_position < start or record.end_position > end:
                raise ValueError("Transcript is outside the source gene span.")
            if record.ensembl_transcript_id in seen:
                raise ValueError("Duplicate transcript identity in response.")
            seen.add(record.ensembl_transcript_id)
            records.append(record)
        return NormalizedTranscriptBatch(
            ensembl_gene_id=gene["id"],
            taxonomy_id=str(taxonomy),
            source_release=str(release),
            retrieved_at=datetime.now(UTC),
            transcripts=records,
        )
