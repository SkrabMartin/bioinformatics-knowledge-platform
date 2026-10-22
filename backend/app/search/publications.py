import re
from typing import Any

from sqlalchemy import Integer, and_, case, cast, func, literal, literal_column, or_, select
from sqlalchemy.sql import ColumnElement, Select

from app.models.publication import Publication
from app.services.errors import InvalidInputError


def publication_match(
    query: str, *, postgresql: bool
) -> tuple[ColumnElement[bool], ColumnElement[Any]]:
    query = " ".join(query.split())
    if not query or len(query) > 200:
        raise InvalidInputError("Publication search requires 1-200 non-blank characters.")
    fields = (
        Publication.pubmed_id,
        Publication.doi,
        Publication.title,
        Publication.journal,
        Publication.abstract,
    )
    terms = re.findall(r"[\w.:-]+", query) or [query]
    conditions = []
    for term in terms:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(or_(*(field.ilike(f"%{escaped}%", escape="\\") for field in fields)))
    condition = and_(*conditions)
    score: ColumnElement[Any] = case(
        (
            or_(
                func.lower(Publication.pubmed_id) == query.lower(),
                func.lower(Publication.doi) == query.lower(),
            ),
            1300,
        ),
        (func.lower(Publication.title) == query.lower(), 1200),
        else_=400,
    )
    if postgresql:
        document = func.to_tsvector(
            literal_column("'simple'::regconfig"),
            func.coalesce(Publication.title, literal_column("''"))
            + literal_column("' '")
            + func.coalesce(Publication.abstract, literal_column("''"))
            + literal_column("' '")
            + func.coalesce(Publication.journal, literal_column("''")),
        )
        tsquery = func.websearch_to_tsquery(literal_column("'simple'::regconfig"), query)
        condition = or_(condition, document.bool_op("@@")(tsquery))
        score = score + cast(func.least(func.ts_rank_cd(document, tsquery) * 100, 99), Integer)
    return condition, score


def publication_statement(query: str, *, postgresql: bool) -> Select[Any]:
    condition, score = publication_match(query, postgresql=postgresql)
    columns: list[ColumnElement[Any]] = [
        literal("publication").label("entity_type"),
        Publication.id.label("entity_id"),
        Publication.title.label("primary_label"),
        Publication.journal.label("secondary_label"),
        Publication.abstract.label("description"),
        cast(literal(None), Publication.journal.type).label("organism_name"),
        cast(literal(None), Publication.journal.type).label("organism_taxonomy_id"),
        Publication.source.label("source"),
    ]
    for i, (name, value) in enumerate(
        (
            ("pubmed_id", Publication.pubmed_id),
            ("doi", Publication.doi),
            ("title", Publication.title),
            ("journal", Publication.journal),
            ("abstract", Publication.abstract),
        ),
        1,
    ):
        columns.extend([literal(name).label(f"field_{i}_name"), value.label(f"field_{i}_value")])
    return select(*columns, score.label("score")).where(condition)
