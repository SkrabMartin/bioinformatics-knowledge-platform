# Unified search coverage — 0.13.0

This increment advances long-term roadmap Phase 6. The existing PostgreSQL search
now includes ten stored entity categories: gene, protein, organism, publication,
transcript, disease, variant, pathway, biological_process and molecular_function.
The search page offers the same categories, counts and shareable filters. Existing
suggestions draw from the expanded catalogue and retain valid entity-detail links.
No external lookup or new biological import is triggered by searching.

## Searchable content

| Added category | Stored fields used |
|---|---|
| Transcript | Ensembl transcript accession and stored version, display name, parent gene symbol, biotype, assembly |
| Disease | Name, MONDO ID, Disease Ontology ID, description |
| Variant | rsID, HGVS, description; a variant with only HGVS remains searchable |
| Pathway | Name, provider-scoped source identifier, description |
| Biological process / molecular function | GO ID, name, description; categories remain separated by their stored kind |

Transcript results carry their stored organism context; searching a gene symbol can
return its imported transcripts. Exact transcript accessions and stored versions rank
above name/prefix matches. A whole versioned Ensembl transcript identifier restricts
that category to the exact stored version; an unobserved version does not resolve to
a different transcript version. This is a current-record lookup, not historical
transcript reconstruction. Gene identifier version resolution remains the separate
source-evidenced registry API documented in GENE_IDENTIFIERS.md.

Disease, variant, pathway and GO links use internal numeric IDs. Transcript links
use the stable transcript accession. A pathway without a stored organism is retained
with null organism context. No disease/variant/pathway/GO assertions are inferred
from matching text. Result source labels are retained; detailed provenance remains
available on record detail pages.

## API compatibility and ranking

`GET /api/v1/search?q=...` and `/api/search?q=...` retain pagination, result fields,
matched fields and deterministic ranking. Existing four categories and their filters
remain supported. `counts` gains six nonnegative fields, and default all-category
results can now contain the six new entity discriminators. Clients with a closed
entity enum must add them or explicitly request the original categories with repeated
`type=gene&type=protein&type=organism&type=publication` parameters.

`counts.total` covers all matching categories; `total` and `pages` reflect the selected
filter(s). A result appears once per entity, even when several fields match. The two
GO categories do not share results. Suggestions use the same expanded selection and
ranking, bounded to the requested limit. Old frontend responses lacking new counts
are rendered as zero for those categories.

Matching preserves escaped literal LIKE wildcards, case-insensitive partial matching,
multi-term matching and PostgreSQL full-text ranking. Exact identity/symbol weighting
and the existing deterministic label/type/ID tie-breaks remain. Expanding the default
catalogue can naturally change which records appear on a combined first page.

## Runtime and scope limits

Search and suggestions now apply a five-second application query budget and
transaction-local PostgreSQL statement deadlines. Exceeding it returns a safe 503
`search_timeout`, not fabricated empty results or a partial response. This bounds
query execution rather than promising a strict end-to-end HTTP latency. SQLite test
fallback preserves matching behavior without PostgreSQL full-text ranking.

This release requires no schema migration. Newly included full-text expressions do
not have dedicated new GIN indexes; performance at larger scale must be measured
before adding those indexes or a separate search engine. Existing source data and
empty catalogues are preserved. This does not implement fuzzy matching, semantic
search, ontology-synonym expansion, an external search engine, global identifier
resolution or every future roadmap entity. It is not completion of Phase 6.

## Verification and rollout

Tests cover every added category, both GO kinds, exact stored transcript versions,
unknown-version rejection, HGVS-only variants, missing pathway organism, parent-gene
matching, filters, counts, ranking, suggestions, escaped wildcards and safe deadline
failure. The added catalogue contracts also run on isolated PostgreSQL to exercise
actual unions, full-text ranking and polymorphic term filtering.

Before rollout, retain old backend/frontend images and restore a new private database
backup to an isolated database. Compare catalogue/identifier counts and run search
against the restored data. Use the established VPS/Compose wrapper for build/update,
then verify public HTTPS search, filters, suggestions, SPA bundle and unchanged
catalogue totals. Rollback uses the old application images; no database downgrade
or reset is necessary.

Release checks passed 161 backend and 43 frontend tests plus migration/model, lint,
formatting, typing and build checks. The restored starter database returned 42 TP53
results (one gene, one protein, 40 transcripts). Its other new categories remained
empty, as expected from their stored data. No synthetic test record was imported.

The deployed 0.13 instance passed public HTTPS checks for TP53 transcript filters,
exact observed transcript versions, unknown-version rejection, suggestions, empty
catalogue filters and the new SPA bundle. The original three genes, three proteins
and 128 transcripts remained available, and public write methods stayed blocked.

Release 0.14 additionally includes the `phenotype` category (eleven categories in
total). HPO ID/name/description matching, counts, suggestions and numeric detail
links follow the same search contract. See [phenotypes](PHENOTYPES.md).

Release 0.16 additionally includes `cellular_component` GO terms, increasing the
supported search categories to twelve. See [cellular components](CELLULAR_COMPONENTS.md).

Release 0.18 adds `dataset` accession/title/summary matching, counts, suggestions and
detail links (thirteen categories). See [dataset discovery](DATASETS.md).
