import re
from collections.abc import Iterable, Sequence
from math import ceil
from typing import Any
from urllib.parse import quote

from sqlalchemy import (
    Integer,
    String,
    and_,
    case,
    cast,
    func,
    literal,
    literal_column,
    or_,
    select,
    union_all,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql import ColumnElement, Select

from app.models import Gene, Organism, Protein
from app.schemas.search import (
    SearchCounts,
    SearchEntityType,
    SearchMatchedField,
    SearchOrganism,
    SearchResponse,
    SearchResult,
    SearchSuggestion,
    SearchSuggestionsResponse,
)
from app.search.publications import publication_statement
from app.services.errors import InvalidInputError

MAX_QUERY_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 320
ENTITY_ORDER = (
    SearchEntityType.GENE,
    SearchEntityType.PROTEIN,
    SearchEntityType.ORGANISM,
    SearchEntityType.PUBLICATION,
)
SearchField = ColumnElement[Any] | InstrumentedAttribute[Any]


class SearchService:
    """Rank and paginate a unified database-side entity search."""

    def __init__(self, session: Session) -> None:
        self.session = session
        bind = session.get_bind()
        self.is_postgresql = bind.dialect.name == "postgresql"

    def search(
        self,
        query: str,
        *,
        page: int,
        page_size: int,
        entity_types: Sequence[SearchEntityType] | None = None,
    ) -> SearchResponse:
        normalized = _normalize_query(query)
        terms = _query_terms(normalized)
        statements = self._statements(normalized, terms)
        category_counts = {
            entity_type: self._count(statement) for entity_type, statement in statements.items()
        }
        selected_types = [
            entity_type
            for entity_type in ENTITY_ORDER
            if not entity_types or entity_type in entity_types
        ]
        total = sum(category_counts[entity_type] for entity_type in selected_types)
        rows = self._ranked_rows(statements, selected_types, page=page, page_size=page_size)
        counts = SearchCounts(
            gene=category_counts[SearchEntityType.GENE],
            protein=category_counts[SearchEntityType.PROTEIN],
            organism=category_counts[SearchEntityType.ORGANISM],
            publication=category_counts[SearchEntityType.PUBLICATION],
            total=sum(category_counts.values()),
        )
        return SearchResponse(
            query=normalized,
            items=[_result_from_row(row, normalized, terms) for row in rows],
            counts=counts,
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size) if total else 0,
        )

    def suggestions(self, query: str, *, limit: int) -> SearchSuggestionsResponse:
        normalized = _normalize_query(query)
        terms = _query_terms(normalized)
        rows = self._ranked_rows(
            self._statements(normalized, terms), ENTITY_ORDER, page=1, page_size=limit
        )
        results = [_result_from_row(row, normalized, terms) for row in rows]
        return SearchSuggestionsResponse(
            query=normalized,
            items=[
                SearchSuggestion(
                    entity_type=item.entity_type,
                    value=item.primary_label,
                    secondary_label=item.secondary_label,
                    href=item.href,
                )
                for item in results
            ],
        )

    def _ranked_rows(
        self,
        statements: dict[SearchEntityType, Select[Any]],
        selected_types: Sequence[SearchEntityType],
        *,
        page: int,
        page_size: int,
    ) -> list[RowMapping]:
        combined = union_all(
            *(statements[entity_type] for entity_type in selected_types)
        ).subquery()
        statement = (
            select(combined)
            .order_by(
                combined.c.score.desc(),
                case((combined.c.source == "development_fixture", 1), else_=0),
                func.lower(combined.c.primary_label),
                combined.c.entity_type,
                combined.c.entity_id,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.execute(statement).mappings().all())

    def _statements(self, query: str, terms: Sequence[str]) -> dict[SearchEntityType, Select[Any]]:
        return {
            SearchEntityType.GENE: self._gene_statement(query, terms),
            SearchEntityType.PROTEIN: self._protein_statement(query, terms),
            SearchEntityType.ORGANISM: self._organism_statement(query, terms),
            SearchEntityType.PUBLICATION: publication_statement(
                query, postgresql=self.is_postgresql
            ),
        }

    def _gene_statement(self, query: str, terms: Sequence[str]) -> Select[Any]:
        fields = (
            Gene.symbol,
            Gene.name,
            Gene.ncbi_gene_id,
            Gene.ensembl_gene_id,
            Gene.description,
        )
        match_condition, full_text_rank = self._match_and_rank(
            fields,
            query,
            terms,
            full_text_fields=(
                Gene.symbol,
                Gene.name,
                Gene.description,
                Gene.ncbi_gene_id,
                Gene.ensembl_gene_id,
            ),
        )
        base_score = _score(
            query,
            exact_identifier=(Gene.ncbi_gene_id, Gene.ensembl_gene_id),
            exact_primary=(Gene.symbol,),
            exact_name=(Gene.name,),
            prefix_identifier=(Gene.ncbi_gene_id, Gene.ensembl_gene_id),
            prefix_primary=(Gene.symbol,),
            prefix_name=(Gene.name,),
        )
        return (
            select(
                literal(SearchEntityType.GENE.value).label("entity_type"),
                Gene.id.label("entity_id"),
                Gene.symbol.label("primary_label"),
                Gene.name.label("secondary_label"),
                Gene.description.label("description"),
                Organism.scientific_name.label("organism_name"),
                Organism.taxonomy_id.label("organism_taxonomy_id"),
                Gene.source.label("source"),
                literal("symbol").label("field_1_name"),
                Gene.symbol.label("field_1_value"),
                literal("name").label("field_2_name"),
                Gene.name.label("field_2_value"),
                literal("ncbi_gene_id").label("field_3_name"),
                Gene.ncbi_gene_id.label("field_3_value"),
                literal("ensembl_gene_id").label("field_4_name"),
                Gene.ensembl_gene_id.label("field_4_value"),
                literal("description").label("field_5_name"),
                Gene.description.label("field_5_value"),
                (base_score + full_text_rank).label("score"),
            )
            .join(Organism, Gene.organism_id == Organism.id)
            .where(match_condition)
        )

    def _protein_statement(self, query: str, terms: Sequence[str]) -> Select[Any]:
        fields = (Protein.accession, Protein.name, Gene.symbol, Protein.function)
        match_condition, full_text_rank = self._match_and_rank(
            fields,
            query,
            terms,
            full_text_fields=(Protein.accession, Protein.name, Protein.function),
        )
        base_score = _score(
            query,
            exact_identifier=(Protein.accession,),
            exact_primary=(),
            exact_name=(Protein.name,),
            prefix_identifier=(Protein.accession,),
            prefix_primary=(),
            prefix_name=(Protein.name,),
            related=(Gene.symbol,),
        )
        return (
            select(
                literal(SearchEntityType.PROTEIN.value).label("entity_type"),
                Protein.id.label("entity_id"),
                Protein.accession.label("primary_label"),
                Protein.name.label("secondary_label"),
                Protein.function.label("description"),
                Organism.scientific_name.label("organism_name"),
                Organism.taxonomy_id.label("organism_taxonomy_id"),
                Protein.source.label("source"),
                literal("accession").label("field_1_name"),
                Protein.accession.label("field_1_value"),
                literal("name").label("field_2_name"),
                Protein.name.label("field_2_value"),
                literal("gene_symbol").label("field_3_name"),
                Gene.symbol.label("field_3_value"),
                literal("function").label("field_4_name"),
                Protein.function.label("field_4_value"),
                _null_text().label("field_5_name"),
                _null_text().label("field_5_value"),
                (base_score + full_text_rank).label("score"),
            )
            .join(Organism, Protein.organism_id == Organism.id)
            .outerjoin(Gene, Protein.gene_id == Gene.id)
            .where(match_condition)
        )

    def _organism_statement(self, query: str, terms: Sequence[str]) -> Select[Any]:
        fields = (Organism.taxonomy_id, Organism.scientific_name, Organism.common_name)
        match_condition, full_text_rank = self._match_and_rank(
            fields,
            query,
            terms,
            full_text_fields=(
                Organism.scientific_name,
                Organism.common_name,
                Organism.taxonomy_id,
            ),
        )
        base_score = _score(
            query,
            exact_identifier=(Organism.taxonomy_id,),
            exact_primary=(Organism.scientific_name,),
            exact_name=(Organism.common_name,),
            prefix_identifier=(Organism.taxonomy_id,),
            prefix_primary=(Organism.scientific_name,),
            prefix_name=(Organism.common_name,),
        )
        return select(
            literal(SearchEntityType.ORGANISM.value).label("entity_type"),
            Organism.id.label("entity_id"),
            Organism.scientific_name.label("primary_label"),
            Organism.common_name.label("secondary_label"),
            _null_text().label("description"),
            Organism.scientific_name.label("organism_name"),
            Organism.taxonomy_id.label("organism_taxonomy_id"),
            Organism.source.label("source"),
            literal("taxonomy_id").label("field_1_name"),
            Organism.taxonomy_id.label("field_1_value"),
            literal("scientific_name").label("field_2_name"),
            Organism.scientific_name.label("field_2_value"),
            literal("common_name").label("field_3_name"),
            Organism.common_name.label("field_3_value"),
            _null_text().label("field_4_name"),
            _null_text().label("field_4_value"),
            _null_text().label("field_5_name"),
            _null_text().label("field_5_value"),
            (base_score + full_text_rank).label("score"),
        ).where(match_condition)

    def _match_and_rank(
        self,
        fields: Sequence[SearchField],
        query: str,
        terms: Sequence[str],
        full_text_fields: Sequence[SearchField] | None = None,
    ) -> tuple[ColumnElement[bool], ColumnElement[int]]:
        partial_match = _partial_match(fields, query, terms)
        if not self.is_postgresql:
            return partial_match, literal(0)
        document = _search_document(full_text_fields or fields)
        ts_query = func.websearch_to_tsquery(literal_column("'simple'::regconfig"), query)
        full_text_match = document.bool_op("@@")(ts_query)
        rank = cast(func.least(func.ts_rank_cd(document, ts_query) * 100, 99), Integer)
        return or_(partial_match, full_text_match), rank

    def _count(self, statement: Select[Any]) -> int:
        return self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0


def _normalize_query(query: str) -> str:
    normalized = " ".join(query.split())
    if not normalized:
        raise InvalidInputError("Search query must contain at least one non-whitespace character.")
    if len(normalized) > MAX_QUERY_LENGTH:
        raise InvalidInputError(f"Search query cannot exceed {MAX_QUERY_LENGTH} characters.")
    return normalized


def _query_terms(query: str) -> list[str]:
    return [term.casefold() for term in re.findall(r"[\w.:-]+", query) if term]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _partial_match(
    fields: Sequence[SearchField], query: str, terms: Sequence[str]
) -> ColumnElement[bool]:
    phrase = f"%{_escape_like(query)}%"
    phrase_match = or_(*(field.ilike(phrase, escape="\\") for field in fields))
    if not terms:
        return phrase_match
    term_matches = [
        or_(*(field.ilike(f"%{_escape_like(term)}%", escape="\\") for field in fields))
        for term in terms
    ]
    return or_(phrase_match, and_(*term_matches))


def _score(
    query: str,
    *,
    exact_identifier: Sequence[SearchField],
    exact_primary: Sequence[SearchField],
    exact_name: Sequence[SearchField],
    prefix_identifier: Sequence[SearchField],
    prefix_primary: Sequence[SearchField],
    prefix_name: Sequence[SearchField],
    related: Sequence[SearchField] = (),
) -> ColumnElement[int]:
    lowered = query.casefold()
    prefix = f"{_escape_like(query)}%"
    return case(
        (_exact_any(exact_identifier, lowered), 1300),
        (_exact_any(exact_primary, lowered), 1200),
        (_exact_any(exact_name, lowered), 1000),
        (_prefix_any(prefix_identifier, prefix), 950),
        (_prefix_any(prefix_primary, prefix), 900),
        (_exact_any(related, lowered), 850),
        (_prefix_any(prefix_name, prefix), 700),
        (_prefix_any(related, prefix), 600),
        else_=400,
    )


def _exact_any(fields: Sequence[SearchField], lowered: str) -> ColumnElement[bool]:
    if not fields:
        return literal(False)
    return or_(*(func.lower(field) == lowered for field in fields))


def _prefix_any(fields: Sequence[SearchField], pattern: str) -> ColumnElement[bool]:
    if not fields:
        return literal(False)
    return or_(*(field.ilike(pattern, escape="\\") for field in fields))


def _search_document(fields: Sequence[SearchField]) -> ColumnElement[Any]:
    pieces: list[ColumnElement[Any]] = [
        func.coalesce(field, literal_column("''")) for field in fields
    ]
    combined: ColumnElement[Any] = pieces[0]
    for piece in pieces[1:]:
        combined = combined + literal_column("' '") + piece
    return func.to_tsvector(literal_column("'simple'::regconfig"), combined)


def _null_text() -> ColumnElement[str]:
    return cast(literal(None), String())


def _result_from_row(row: RowMapping, query: str, terms: Sequence[str]) -> SearchResult:
    entity_type = SearchEntityType(str(row["entity_type"]))
    primary_label = str(row["primary_label"])
    matched_fields: list[SearchMatchedField] = []
    for index in range(1, 6):
        field_name = row[f"field_{index}_name"]
        value = row[f"field_{index}_value"]
        if (
            isinstance(field_name, str)
            and isinstance(value, str)
            and _value_matches(value, query, terms)
        ):
            matched_fields.append(
                SearchMatchedField(field=field_name, value=_excerpt(value, query, terms))
            )

    organism = None
    if entity_type is not SearchEntityType.ORGANISM and isinstance(row["organism_name"], str):
        taxonomy_id = row["organism_taxonomy_id"]
        organism = SearchOrganism(
            scientific_name=row["organism_name"],
            taxonomy_id=taxonomy_id if isinstance(taxonomy_id, str) else None,
        )
    description = row["description"]
    description_text = (
        _excerpt(description, query, terms)
        if isinstance(description, str) and description
        else None
    )
    return SearchResult(
        entity_type=entity_type,
        entity_id=int(row["entity_id"]),
        primary_label=primary_label,
        secondary_label=(
            row["secondary_label"] if isinstance(row["secondary_label"], str) else None
        ),
        description=description_text,
        organism=organism,
        source=str(row["source"]),
        href=(
            f"/publication/{row['entity_id']}"
            if entity_type is SearchEntityType.PUBLICATION
            else _entity_href(entity_type, primary_label, row["organism_taxonomy_id"])
        ),
        score=int(row["score"]),
        matched_fields=matched_fields,
    )


def _entity_href(
    entity_type: SearchEntityType, primary_label: str, taxonomy_id: object
) -> str | None:
    encoded = quote(primary_label, safe="")
    if entity_type is SearchEntityType.GENE:
        suffix = (
            f"?taxonomy_id={quote(taxonomy_id, safe='')}" if isinstance(taxonomy_id, str) else ""
        )
        return f"/gene/{encoded}{suffix}"
    if entity_type is SearchEntityType.PROTEIN:
        return f"/protein/{encoded}"
    return None


def _value_matches(value: str, query: str, terms: Iterable[str]) -> bool:
    lowered = value.casefold()
    return query.casefold() in lowered or any(term in lowered for term in terms)


def _excerpt(value: str, query: str, terms: Sequence[str]) -> str:
    compact = " ".join(value.split())
    if len(compact) <= MAX_DESCRIPTION_LENGTH:
        return compact
    lowered = compact.casefold()
    needles = [query.casefold(), *terms]
    positions = [lowered.find(needle) for needle in needles if needle and needle in lowered]
    match_position = min(positions) if positions else 0
    start = max(0, match_position - 90)
    end = min(len(compact), start + MAX_DESCRIPTION_LENGTH)
    prefix = "…" if start else ""
    suffix = "…" if end < len(compact) else ""
    return f"{prefix}{compact[start:end]}{suffix}"
