import calendar
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from xml.etree.ElementTree import Element, ParseError

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring
from pydantic import HttpUrl, ValidationError

from app.ingestion.publications import NormalizedPublication
from app.integrations.errors import (
    IntegrationConfigurationError,
    UpstreamNotFoundError,
    UpstreamResponseError,
)
from app.integrations.http import TextHttpClient


class PubMedAdapter:
    """Bounded EFetch metadata and explicit ELink links; never infer links from text."""

    provider = "NCBI PubMed"

    def __init__(
        self,
        http: TextHttpClient,
        *,
        base_url: str,
        tool: str,
        email: str | None,
        api_key: str | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not email or email.endswith("@example.org"):
            raise IntegrationConfigurationError(
                self.provider,
                "Configure BKP_NCBI_EMAIL with the application owner's monitored address.",
            )
        self.http, self.base_url, self.sleeper = http, base_url.rstrip("/"), sleeper
        self.params: dict[str, str | int] = {"tool": tool, "email": email}
        if api_key:
            self.params["api_key"] = api_key

    def fetch_publication(self, pubmed_id: str) -> NormalizedPublication:
        if not re.fullmatch(r"[1-9][0-9]{0,31}", pubmed_id):
            raise ValueError("PubMed ID must be a positive numeric identifier.")
        xml = self.http.get_text(
            f"{self.base_url}/efetch.fcgi",
            params={
                **self.params,
                "db": "pubmed",
                "id": pubmed_id,
                "retmode": "xml",
            },
            not_found_message=f"PubMed {pubmed_id} was not found.",
        )
        record = parse_publication(xml, pubmed_id)
        # At most two sequential requests per import; conservative spacing without an API key.
        self.sleeper(0.35)
        payload = self.http.get_json(
            f"{self.base_url}/elink.fcgi",
            params={
                **self.params,
                "dbfrom": "pubmed",
                "db": "gene",
                "id": pubmed_id,
                "linkname": "pubmed_gene",
                "retmode": "json",
            },
            not_found_message=f"PubMed links for {pubmed_id} were not found.",
        )
        try:
            linksets = payload["linksets"]
            if not isinstance(linksets, list) or len(linksets) != 1:
                raise ValueError
            linkset = linksets[0]
            if [str(value) for value in linkset["ids"]] != [pubmed_id] or "error" in linkset:
                raise ValueError
            ids: set[str] = set()
            for group in linkset.get("linksetdbs", []):
                if group["linkname"] == "pubmed_gene":
                    for value in group["links"]:
                        identifier = str(value)
                        if not re.fullmatch(r"[1-9][0-9]*", identifier):
                            raise ValueError
                        ids.add(identifier)
            record.linked_ncbi_gene_ids = sorted(ids)
            if len(ids) > 10000:
                raise ValueError
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamResponseError(
                self.provider, "PubMed returned invalid structured gene links."
            ) from exc
        return record


def _text(element: Element | None) -> str | None:
    return " ".join("".join(element.itertext()).split()) or None if element is not None else None


def parse_publication(xml: str, pubmed_id: str) -> NormalizedPublication:
    try:
        root = fromstring(xml, forbid_entities=True, forbid_external=True)
    except (ParseError, DefusedXmlException) as exc:
        raise UpstreamResponseError(
            "NCBI PubMed", "PubMed returned malformed or unsafe XML."
        ) from exc
    articles = root.findall("PubmedArticle")
    if not articles and not list(root) and root.tag == "PubmedArticleSet":
        raise UpstreamNotFoundError("NCBI PubMed", f"PubMed {pubmed_id} was not found.")
    if len(articles) != 1 or _text(articles[0].find("MedlineCitation/PMID")) != pubmed_id:
        raise UpstreamResponseError(
            "NCBI PubMed", "PubMed returned an unsupported or mismatched citation."
        )
    entry = articles[0]
    article = entry.find("MedlineCitation/Article")
    if article is None:
        raise UpstreamResponseError("NCBI PubMed", "PubMed citation has no article metadata.")
    doi_values = {
        _text(node) for node in entry.findall("PubmedData/ArticleIdList/ArticleId[@IdType='doi']")
    }
    doi_values.discard(None)
    if len(doi_values) > 1:
        raise UpstreamResponseError(
            "NCBI PubMed", "PubMed citation has conflicting DOI identifiers."
        )
    authors = []
    for author in article.findall("AuthorList/Author"):
        name = _text(author.find("CollectiveName"))
        if name is None:
            name = " ".join(
                filter(
                    None,
                    [
                        _text(author.find("ForeName")) or _text(author.find("Initials")),
                        _text(author.find("LastName")),
                    ],
                )
            )
        if name:
            authors.append(name)
    abstract_parts = []
    for section in article.findall("Abstract/AbstractText"):
        text = _text(section)
        if text:
            label = section.get("Label")
            abstract_parts.append(f"{label}: {text}" if label else text)
    date_node = article.find("Journal/JournalIssue/PubDate")
    raw_date = (
        " ".join(filter(None, (_text(child) for child in date_node)))
        if date_node is not None
        else None
    )
    partial_date = None
    if date_node is not None:
        year = _text(date_node.find("Year"))
        medline = _text(date_node.find("MedlineDate"))
        if year is None and medline:
            match = re.match(r"([0-9]{4})\b", medline)
            year = match[1] if match else None
        if year:
            partial_date = year
            month = _text(date_node.find("Month"))
            month_number = next(
                (
                    i
                    for i in range(1, 13)
                    if month
                    and month.lower()
                    in (
                        calendar.month_abbr[i].lower(),
                        calendar.month_name[i].lower(),
                        str(i),
                        f"{i:02d}",
                    )
                ),
                None,
            )
            if month_number:
                partial_date += f"-{month_number:02d}"
                day = _text(date_node.find("Day"))
                if day and day.isdigit():
                    partial_date += f"-{int(day):02d}"
    try:
        return NormalizedPublication(
            pubmed_id=pubmed_id,
            doi=next(iter(doi_values), None),
            title=_text(article.find("ArticleTitle")) or "",
            abstract="\n\n".join(abstract_parts) or None,
            journal=_text(article.find("Journal/Title")),
            authors=authors,
            publication_date=partial_date,
            publication_date_text=raw_date,
            source="NCBI PubMed",
            source_identifier=pubmed_id,
            source_url=HttpUrl(f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"),
            imported_at=datetime.now(UTC),
        )
    except ValidationError as exc:
        raise UpstreamResponseError(
            "NCBI PubMed", "PubMed citation failed normalized metadata validation."
        ) from exc
