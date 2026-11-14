"""Explicit lexical hints only; never resolve identifiers approximately."""

import time
import unicodedata
from typing import Any, Literal
from urllib.parse import quote, urlencode

from pydantic import Field
from sqlalchemy import func, literal, select, union_all
from sqlalchemy.orm import Session

from app.models import Gene, Organism, Protein, Publication
from app.schemas.common import ApiModel
from app.search.service import SearchService
from app.services.errors import ApplicationError, InvalidInputError

NameType = Literal["gene", "protein", "organism", "publication"]
THRESHOLD = 0.55


class NameHint(ApiModel):
    entity_type: NameType
    entity_id: int
    label: str
    matched_name: str
    match_field: str
    source: str
    href: str | None
    similarity: float = Field(ge=0, le=1)


class NameHints(ApiModel):
    query: str
    method: Literal["pg_trgm_word_similarity"] = "pg_trgm_word_similarity"
    threshold: float = THRESHOLD
    items: list[NameHint]


def normalize_name_query(value: str) -> str:
    value = unicodedata.normalize("NFC", " ".join(value.split()))
    if (
        not 4 <= len(value) <= 120
        or not all(char.isalpha() or char in " '-" for char in value)
        or not any(len(word) >= 4 for word in value.split())
        or (len(value.split()) == 1 and value.isupper())
    ):
        raise InvalidInputError(
            "Name hints require 4-120 characters of name text; identifiers are not corrected."
        )
    return value


def name_hints(
    session: Session, query: str, limit: int = 6, kind: NameType | None = None
) -> NameHints:
    query = normalize_name_query(query)
    if not 1 <= limit <= 8:
        raise InvalidInputError("Name hint limit must be between 1 and 8.")
    if session.get_bind().dialect.name != "postgresql":
        error = ApplicationError("Similar-name hints require PostgreSQL pg_trgm.")
        error.code, error.status_code = "name_hints_unavailable", 503
        raise error
    search = SearchService(session)
    search.deadline = time.monotonic() + 3
    search._execute(
        select(func.set_config("pg_trgm.word_similarity_threshold", str(THRESHOLD), True))
    )
    # Existing raw-column GIN trigram indexes support %>; no lower/coalesce wrapper.
    specs: tuple[tuple[NameType, Any, Any, Any, str], ...] = (
        ("gene", Gene, Gene.symbol, Gene.name, "name"),
        ("protein", Protein, Protein.accession, Protein.name, "name"),
        (
            "organism",
            Organism,
            Organism.scientific_name,
            Organism.scientific_name,
            "scientific_name",
        ),
        ("organism", Organism, Organism.scientific_name, Organism.common_name, "common_name"),
        ("publication", Publication, Publication.title, Publication.title, "title"),
    )
    branches = []
    for entity_type, model, label, name, field in specs:
        if kind is not None and entity_type != kind:
            continue
        score = func.word_similarity(query, name)
        statement = select(
            literal(entity_type).label("entity_type"),
            model.id.label("entity_id"),
            label.label("label"),
            name.label("matched_name"),
            literal(field).label("match_field"),
            model.source.label("source"),
            score.label("similarity"),
            (Organism.taxonomy_id if entity_type == "gene" else literal(None)).label("taxonomy"),
        ).where(name.bool_op("%>")(query))
        if entity_type == "gene":
            statement = statement.join(Organism, Gene.organism_id == Organism.id)
        # Per-field top-k: bounded returned candidates, not a claim of bounded index work.
        branch = statement.order_by(score.desc(), label, model.id).limit(limit).subquery()
        branches.append(select(branch))
    combined = union_all(*branches).subquery()
    rows = search._execute(
        select(combined).order_by(
            combined.c.similarity.desc(),
            combined.c.label,
            combined.c.entity_type,
            combined.c.entity_id,
            combined.c.match_field,
        )
    ).mappings()
    items: list[NameHint] = []
    seen = set()
    for row in rows:
        identity = (row["entity_type"], row["entity_id"])
        if identity in seen:
            continue
        seen.add(identity)
        entity_type = row["entity_type"]
        if entity_type == "gene":
            href = (
                f"/gene/{quote(row['label'], safe='')}"
                f"?taxonomy_id={quote(row['taxonomy'], safe='')}"
                if row["taxonomy"]
                else None
            )
        elif entity_type == "protein":
            href = f"/protein/{quote(row['label'], safe='')}"
        elif entity_type == "publication":
            href = f"/publication/{row['entity_id']}"
        else:
            href = "/search?" + urlencode({"q": row["label"], "type": "organism"})
        items.append(
            NameHint(**{key: row[key] for key in NameHint.model_fields if key != "href"}, href=href)
        )
        if len(items) == limit:
            break
    return NameHints(query=query, items=items)
