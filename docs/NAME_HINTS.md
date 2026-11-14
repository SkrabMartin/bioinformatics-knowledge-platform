# Similar stored names — 0.22.0

This starts a bounded Phase 15 follow-up on existing PostgreSQL search indexes.
The database currently has a small starter catalogue; a separate search cluster
is not justified by its measured size. PostgreSQL remains the source of truth and
no external index, new dependency, data import or schema migration is introduced.

## Separate lexical hints

`GET /api/v1/search/name-suggestions?q=Homo%20sapines&limit=6&type=organism`
returns similar **stored names**. An optional `type` selects gene, protein,
organism or publication. The search page offers an explicit Find similar names
button for eligible text and supported categories. It makes no extra hint request
until clicked. Hints do not change the user's query or the main search result
counts/ranking, and existing autocomplete/identifier search contracts are unchanged.

Only gene.name, protein.name, organism.scientific_name/common_name and publication.title
participate. Gene symbols, aliases, accessions, taxonomy IDs, DOI/PMID, variant
identifiers, transcript versions and other biological identifiers are not fuzzy
matched. A gene/protein's canonical label/identifier may be displayed, but the
matched field and stored name are shown separately. A text hint creates no
biological relationship and is not identifier resolution or scientific evidence.

Input is whitespace/NFC normalized and restricted to 4–120 characters of letters,
spaces, apostrophes and hyphens, with a word of at least four characters. Digits,
other punctuation and a single all-uppercase token are rejected. This conservative
heuristic excludes many identifiers but is not a universal classifier of biological
symbols: lowercase alphabetic input can be name text. There is no silent correction
of an identifier, no synonym expansion and no claim of semantic relevance.

Each hint retains entity type/ID, canonical label, matched name/field, source,
valid navigation link when available and a lexical similarity score. Organism
links open an ordinary search for the stored scientific name. Scores are not
probabilities or confidence in biology. Missing names remain missing.

## PostgreSQL implementation and bounds

The existing raw-column GIN pg_trgm indexes support the `%>` word-similarity
operator. `word_similarity(query, stored_name)` determines the ordering; the fixed
transaction-local threshold is 0.55. See the [PostgreSQL 17 documentation](https://www.postgresql.org/docs/17/pgtrgm.html).
No lowercase/coalesce wrapper prevents use of the original indexed field.

The query takes top-k per indexed field, combines candidates, orders them
predictably and deduplicates by type/ID, keeping the strongest field. The limit
is 1–8 hints, with at most five field branches. This bounds returned candidates,
not index/heap scan work or sort cost. A three-second application/statement budget
uses the existing safe `search_timeout` failure instead of fabricated empty hints.
Transaction-local settings are rolled back on session close, avoiding pool leaks.

SQLite has no equivalent implemented: it returns explicit 503
`name_hints_unavailable`, not approximate fabricated parity. PostgreSQL deployments
must already have the pg_trgm extension/indexes from existing migrations. A result
without hints only means no eligible stored name met this lexical threshold.

The UI preserves the flat research frontend and uses existing source/error/loading
components. Category/query changes reset the optional request. A failed request
has an accessible retry and leaves normal search available.

## Scope and validation

This is not a full Phase 15 implementation: OpenSearch/Elasticsearch, a separate
versioned search index, facets at scale, cross-language synonyms, fuzzy identifiers
and semantic retrieval remain absent. Existing thirteen-category search remains
in place; name hints cover only the four kinds above.

Tests cover input boundaries/Unicode, explicit SQLite unavailability, real
PostgreSQL fuzzy matches, type filters, deduplication, valid source links,
transaction setting cleanup and actual slow-query cancellation. Frontend tests
cover opt-in behavior, identifiers, source labels, score interpretation and errors.
A restored live-data clone is used for the real Homo sapines → Homo sapiens check.
