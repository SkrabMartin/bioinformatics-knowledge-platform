from datetime import UTC, datetime
from typing import Any, cast

from pydantic import HttpUrl, ValidationError

from app.ingestion.models import NormalizedOrganism, NormalizedProtein, SourceProvenance
from app.integrations.errors import UpstreamResponseError
from app.integrations.http import JsonHttpClient


class UniProtAdapter:
    """Translate a UniProtKB JSON entry into a provider-independent protein record."""

    provider = "UniProt"

    def __init__(self, http: JsonHttpClient, *, base_url: str) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")

    def fetch_protein(self, accession: str) -> NormalizedProtein:
        normalized_accession = accession.strip().upper()
        if not normalized_accession:
            raise ValueError("UniProt accession cannot be empty.")
        payload = self.http.get_json(
            f"{self.base_url}/uniprotkb/{normalized_accession}.json",
            not_found_message=f"UniProtKB entry {normalized_accession} was not found.",
        )
        return self._normalize(payload, normalized_accession)

    def _normalize(self, record: dict[str, Any], requested_accession: str) -> NormalizedProtein:
        accession = _string(record.get("primaryAccession"))
        organism_record = record.get("organism")
        if not accession or not isinstance(organism_record, dict):
            raise UpstreamResponseError(
                self.provider,
                f"UniProtKB entry {requested_accession} is missing required identity fields.",
            )

        scientific_name = _string(organism_record.get("scientificName"))
        taxonomy_id = _string(organism_record.get("taxonId"))
        if not scientific_name or not taxonomy_id:
            raise UpstreamResponseError(
                self.provider,
                f"UniProtKB entry {accession} is missing required organism metadata.",
            )

        name = _protein_name(record.get("proteinDescription"))
        if not name:
            raise UpstreamResponseError(
                self.provider, f"UniProtKB entry {accession} has no usable protein name."
            )

        retrieved_at = datetime.now(UTC)
        entry_url = f"https://www.uniprot.org/uniprotkb/{accession}/entry"
        taxonomy_url = f"https://www.uniprot.org/taxonomy/{taxonomy_id}"
        try:
            return NormalizedProtein(
                accession=accession,
                name=name,
                function=_function_text(record.get("comments")),
                sequence_length=_sequence_length(record.get("sequence")),
                gene_symbol=_gene_symbol(record.get("genes")),
                ncbi_gene_id=_database_reference(record.get("uniProtKBCrossReferences"), "GeneID"),
                organism=NormalizedOrganism(
                    scientific_name=scientific_name,
                    common_name=_string(organism_record.get("commonName")),
                    taxonomy_id=taxonomy_id,
                    provenance=SourceProvenance(
                        source="UniProt",
                        source_identifier=taxonomy_id,
                        source_url=HttpUrl(taxonomy_url),
                        retrieved_at=retrieved_at,
                    ),
                ),
                provenance=SourceProvenance(
                    source="UniProt",
                    source_identifier=accession,
                    source_url=HttpUrl(entry_url),
                    retrieved_at=retrieved_at,
                ),
            )
        except ValidationError as exc:
            raise UpstreamResponseError(
                self.provider, f"UniProtKB entry {accession} failed normalized-record validation."
            ) from exc


def _string(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, int):
        return str(value)
    return None


def _protein_name(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    recommended = value.get("recommendedName")
    if isinstance(recommended, dict):
        full_name = recommended.get("fullName")
        if isinstance(full_name, dict) and (name := _string(full_name.get("value"))):
            return name
    submitted = value.get("submissionNames")
    if isinstance(submitted, list):
        for item in submitted:
            if isinstance(item, dict) and isinstance(item.get("fullName"), dict):
                full_name = cast(dict[str, Any], item["fullName"])
                if name := _string(full_name.get("value")):
                    return name
    return None


def _gene_symbol(value: object) -> str | None:
    if not isinstance(value, list):
        return None
    for gene in value:
        if isinstance(gene, dict) and isinstance(gene.get("geneName"), dict):
            gene_name = cast(dict[str, Any], gene["geneName"])
            if symbol := _string(gene_name.get("value")):
                return symbol
    return None


def _function_text(value: object) -> str | None:
    if not isinstance(value, list):
        return None
    statements: list[str] = []
    for comment in value:
        if not isinstance(comment, dict) or comment.get("commentType") != "FUNCTION":
            continue
        texts = comment.get("texts")
        if not isinstance(texts, list):
            continue
        for text in texts:
            if isinstance(text, dict) and (statement := _string(text.get("value"))):
                statements.append(statement)
    return "\n\n".join(statements) or None


def _sequence_length(value: object) -> int | None:
    if not isinstance(value, dict):
        return None
    length = value.get("length")
    return length if isinstance(length, int) and length > 0 else None


def _database_reference(value: object, database: str) -> str | None:
    if not isinstance(value, list):
        return None
    for reference in value:
        if (
            isinstance(reference, dict)
            and reference.get("database") == database
            and (identifier := _string(reference.get("id")))
        ):
            return identifier
    return None
