from datetime import UTC, datetime
from typing import Any, Literal, cast

from pydantic import HttpUrl, ValidationError

from app.ingestion.models import NormalizedGene, NormalizedOrganism, SourceProvenance
from app.integrations.errors import (
    IntegrationConfigurationError,
    UpstreamNotFoundError,
    UpstreamResponseError,
)
from app.integrations.http import JsonHttpClient


class NcbiGeneAdapter:
    """Translate NCBI Gene E-utilities responses into provider-independent records."""

    provider = "NCBI Gene"

    def __init__(
        self,
        http: JsonHttpClient,
        *,
        base_url: str,
        tool: str,
        email: str | None,
        api_key: str | None = None,
    ) -> None:
        if not email:
            raise IntegrationConfigurationError(
                self.provider,
                "NCBI imports require BKP_NCBI_EMAIL so requests identify the application owner.",
            )
        self.http = http
        self.base_url = base_url.rstrip("/")
        self.common_params: dict[str, str | int] = {"tool": tool, "email": email}
        if api_key:
            self.common_params["api_key"] = api_key

    def fetch_gene(self, symbol: str, taxonomy_id: str = "9606") -> NormalizedGene:
        normalized_symbol = symbol.strip()
        if not normalized_symbol:
            raise ValueError("Gene symbol cannot be empty.")

        search_payload = self.http.get_json(
            f"{self.base_url}/esearch.fcgi",
            params={
                **self.common_params,
                "db": "gene",
                "term": (f"{normalized_symbol}[sym] AND {taxonomy_id}[taxid] AND alive[prop]"),
                "retmode": "json",
                "retmax": 2,
            },
            not_found_message=(
                f"NCBI Gene has no current record for {normalized_symbol} "
                f"in taxonomy {taxonomy_id}."
            ),
        )
        identifiers = self._search_identifiers(search_payload, normalized_symbol, taxonomy_id)
        if not identifiers:
            raise UpstreamNotFoundError(
                self.provider,
                f"NCBI Gene has no current record for {normalized_symbol} "
                f"in taxonomy {taxonomy_id}.",
            )
        if len(identifiers) > 1:
            raise UpstreamResponseError(
                self.provider,
                f"NCBI Gene returned multiple exact records for {normalized_symbol} in taxonomy "
                f"{taxonomy_id}; import by symbol is ambiguous.",
            )

        gene_id = identifiers[0]
        summary_payload = self.http.get_json(
            f"{self.base_url}/esummary.fcgi",
            params={
                **self.common_params,
                "db": "gene",
                "id": gene_id,
                "retmode": "json",
                "version": "2.0",
            },
            not_found_message=f"NCBI Gene record {gene_id} was not found.",
        )
        record = self._summary_record(summary_payload, gene_id)
        return self._normalize(record, gene_id)

    def _search_identifiers(
        self, payload: dict[str, Any], symbol: str, taxonomy_id: str
    ) -> list[str]:
        result = payload.get("esearchresult")
        if not isinstance(result, dict) or not isinstance(result.get("idlist"), list):
            raise UpstreamResponseError(
                self.provider,
                f"NCBI Gene returned an unexpected search response for {symbol} in taxonomy "
                f"{taxonomy_id}.",
            )
        identifiers = result["idlist"]
        if not all(isinstance(identifier, str) for identifier in identifiers):
            raise UpstreamResponseError(
                self.provider, "NCBI Gene returned invalid identifiers in its search response."
            )
        return cast(list[str], identifiers)

    def _summary_record(self, payload: dict[str, Any], gene_id: str) -> dict[str, Any]:
        result = payload.get("result")
        if not isinstance(result, dict) or not isinstance(result.get(gene_id), dict):
            raise UpstreamResponseError(
                self.provider, f"NCBI Gene returned no usable summary for GeneID {gene_id}."
            )
        return cast(dict[str, Any], result[gene_id])

    def _normalize(self, record: dict[str, Any], gene_id: str) -> NormalizedGene:
        symbol = _string(record.get("name"))
        gene_name = _string(record.get("description")) or _string(record.get("nomenclaturename"))
        organism_record = record.get("organism")
        if not symbol or not gene_name or not isinstance(organism_record, dict):
            raise UpstreamResponseError(
                self.provider, f"NCBI Gene summary {gene_id} is missing required identity fields."
            )

        scientific_name = _string(organism_record.get("scientificname"))
        tax_id = _string(organism_record.get("taxid"))
        if not scientific_name or not tax_id:
            raise UpstreamResponseError(
                self.provider, f"NCBI Gene summary {gene_id} is missing organism metadata."
            )

        retrieved_at = datetime.now(UTC)
        gene_url = f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}"
        taxonomy_url = f"https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={tax_id}"
        chromosome, start, end, strand = _coordinates(record)
        try:
            return NormalizedGene(
                symbol=symbol,
                name=gene_name,
                description=_string(record.get("summary")),
                organism=NormalizedOrganism(
                    scientific_name=scientific_name,
                    common_name=_string(organism_record.get("commonname")),
                    taxonomy_id=tax_id,
                    provenance=SourceProvenance(
                        source="NCBI Gene",
                        source_identifier=tax_id,
                        source_url=HttpUrl(taxonomy_url),
                        retrieved_at=retrieved_at,
                    ),
                ),
                chromosome=chromosome,
                start_position=start,
                end_position=end,
                strand=strand,
                ncbi_gene_id=gene_id,
                ensembl_gene_id=None,
                provenance=SourceProvenance(
                    source="NCBI Gene",
                    source_identifier=gene_id,
                    source_url=HttpUrl(gene_url),
                    retrieved_at=retrieved_at,
                ),
            )
        except ValidationError as exc:
            raise UpstreamResponseError(
                self.provider, f"NCBI Gene summary {gene_id} failed normalized-record validation."
            ) from exc


def _string(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, int):
        return str(value)
    return None


def _coordinates(
    record: dict[str, Any],
) -> tuple[str | None, int | None, int | None, Literal["+", "-"] | None]:
    chromosome = _string(record.get("chromosome"))
    genomic_info = record.get("genomicinfo")
    if not isinstance(genomic_info, list) or not genomic_info:
        return chromosome, None, None, None
    placement = genomic_info[0]
    if not isinstance(placement, dict):
        return chromosome, None, None, None
    chromosome = _string(placement.get("chrloc")) or chromosome
    raw_start = placement.get("chrstart")
    raw_stop = placement.get("chrstop")
    if not isinstance(raw_start, int) or not isinstance(raw_stop, int):
        return chromosome, None, None, None
    strand: Literal["+", "-"] = "+" if raw_start <= raw_stop else "-"
    return chromosome, min(raw_start, raw_stop) + 1, max(raw_start, raw_stop) + 1, strand
