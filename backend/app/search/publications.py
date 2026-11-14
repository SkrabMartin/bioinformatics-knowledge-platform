import re
from typing import Any

from sqlalchemy import Integer, and_, case, cast, func, literal, literal_column, or_, select
from sqlalchemy.sql import ColumnElement, Select

from app.models.publication import Publication
from app.services.errors import InvalidInputError


def keyword_text(*, postgresql: bool) -> ColumnElement[Any]:
    if postgresql:
        entries = func.json_array_elements_text(Publication.keywords).table_valued("value")
        aggregate = func.string_agg(entries.c.value, literal(" "))
    else:
        entries = func.json_each(Publication.keywords).table_valued("key", "value")
        aggregate = func.group_concat(entries.c.value, literal(" "))
    return func.coalesce(
        select(aggregate).select_from(entries).correlate(Publication).scalar_subquery(), literal("")
    )


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
        keyword_text(postgresql=postgresql),
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
    keywords = keyword_text(postgresql=postgresql)
    terms = re.findall(r"[\w.:-]+", query) or [query]
    keyword_hits = []
    for term in terms:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        keyword_hits.append(keywords.ilike(f"%{escaped}%", escape="\\"))
    keyword_match = or_(*keyword_hits)
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
        field_name = case((keyword_match, "keywords"), else_=name) if i == 5 else literal(name)
        field_value = case((keyword_match, keywords), else_=value) if i == 5 else value
        columns.extend([field_name.label(f"field_{i}_name"), field_value.label(f"field_{i}_value")])
    return select(*columns, score.label("score")).where(condition)
