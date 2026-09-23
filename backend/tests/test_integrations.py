from typing import Any

import httpx2
import pytest

from app.integrations.errors import IntegrationConfigurationError
from app.integrations.http import RetryingJsonClient
from app.integrations.ncbi import NcbiGeneAdapter
from app.integrations.uniprot import UniProtAdapter


def test_ncbi_adapter_normalizes_gene_and_identifies_requests() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if request.url.path.endswith("/esearch.fcgi"):
            return httpx2.Response(200, json={"esearchresult": {"idlist": ["7157"]}})
        return httpx2.Response(
            200,
            json={
                "result": {
                    "uids": ["7157"],
                    "7157": {
                        "uid": "7157",
                        "name": "TP53",
                        "description": "tumor protein p53",
                        "summary": "Provider-supplied summary.",
                        "chromosome": "17",
                        "organism": {
                            "scientificname": "Homo sapiens",
                            "commonname": "human",
                            "taxid": 9606,
                        },
                        "genomicinfo": [{"chrloc": "17", "chrstart": 7687490, "chrstop": 7668421}],
                    },
                }
            },
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        adapter = NcbiGeneAdapter(
            RetryingJsonClient(client, provider="NCBI Gene", max_attempts=2, backoff_seconds=0),
            base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
            tool="bkp_tests",
            email="tests@example.org",
        )
        gene = adapter.fetch_gene("TP53", "9606")

    assert gene.ncbi_gene_id == "7157"
    assert gene.organism.taxonomy_id == "9606"
    assert gene.start_position == 7668422
    assert gene.end_position == 7687491
    assert gene.strand == "-"
    assert all(request.url.params["tool"] == "bkp_tests" for request in requests)
    assert all(request.url.params["email"] == "tests@example.org" for request in requests)


def test_ncbi_adapter_requires_contact_email() -> None:
    class UnusedClient:
        def get_json(self, *_: object, **__: object) -> dict[str, Any]:
            raise AssertionError("HTTP should not be called")

    with pytest.raises(IntegrationConfigurationError, match="BKP_NCBI_EMAIL"):
        NcbiGeneAdapter(
            UnusedClient(),
            base_url="https://example.test",
            tool="bkp_tests",
            email=None,
        )


def test_uniprot_adapter_normalizes_protein() -> None:
    payload = {
        "primaryAccession": "P04637",
        "organism": {"scientificName": "Homo sapiens", "commonName": "Human", "taxonId": 9606},
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}
        },
        "genes": [{"geneName": {"value": "TP53"}}],
        "comments": [
            {"commentType": "FUNCTION", "texts": [{"value": "Provider function text."}]},
            {"commentType": "SUBUNIT", "texts": [{"value": "Not imported in Phase 2."}]},
        ],
        "sequence": {"length": 393},
        "uniProtKBCrossReferences": [{"database": "GeneID", "id": "7157"}],
    }

    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=payload)

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        adapter = UniProtAdapter(
            RetryingJsonClient(client, provider="UniProt", max_attempts=2, backoff_seconds=0),
            base_url="https://rest.uniprot.org",
        )
        protein = adapter.fetch_protein("p04637")

    assert protein.accession == "P04637"
    assert protein.name == "Cellular tumor antigen p53"
    assert protein.function == "Provider function text."
    assert protein.sequence_length == 393
    assert protein.gene_symbol == "TP53"
    assert protein.ncbi_gene_id == "7157"


def test_retrying_client_honors_retry_after() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx2.Response(429, headers={"Retry-After": "2"})
        return httpx2.Response(200, json={"ok": True})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        payload = RetryingJsonClient(
            client,
            provider="Example provider",
            max_attempts=2,
            backoff_seconds=0.5,
            sleeper=delays.append,
        ).get_json("https://example.test/record", not_found_message="Missing")

    assert payload == {"ok": True}
    assert attempts == 2
    assert delays == [2.0]
