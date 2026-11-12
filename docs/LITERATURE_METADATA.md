# Literature metadata and variant references — 0.17.0

This increment advances long-term Phase 10 by retaining PubMed-supplied keywords
and adding explicitly sourced publication–variant links to the existing citation
system. It does not implement full-text collection, NLP relation extraction,
clinical interpretation or automated variant annotation.

## Keywords and provenance

The PubMed adapter reads only `MedlineCitation/KeywordList/Keyword` elements from
the matching citation. The [NLM KeywordList documentation](https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-KeywordList.html)
describes publisher/author and other contributed keyword lists. BKP labels the
flattened values as source keywords rather than claiming every value is an
author keyword, MeSH heading or verified ontology annotation.

Whitespace is normalized and case-insensitive duplicates are removed while retaining
the first display spelling/order. At most 256 keyword nodes and 256 characters per
nonblank value are accepted. Blank XML nodes are skipped; oversized source metadata
fails before ingestion. XML entity/external-reference protections remain enabled.
No keyword is generated from the title, abstract or gene names.

`Publication.keywords` is an additive JSON array with an empty default for old rows.
An empty array means no source values are stored, not that the paper has no topics
or that a provider has no additional metadata. Reimport stores the latest fetched
keyword list with the publication's source/PMID/URL/retrieval metadata. Keyword-level
Owner/MajorTopic flags and historical payload snapshots are not retained in this
increment; keywords do not carry independent immutable assertion history.

## Search and interface

The existing publication catalogue and unified search match the keyword text,
including decoded Unicode values. Existing PMID/DOI ranking and the indexed
publication title/abstract/journal full-text expression remain unchanged. Keyword
matching uses literal escaped partial/multi-term search over database-side JSON
text aggregation; it is not keyword synonym expansion or a specialized keyword
index. Larger corpora require performance measurement before additional indexing.

Unified results retain the existing five matched-field slots. When keyword text
matches, the fifth slot shows a source-keyword excerpt instead of the abstract
excerpt. The complete stored abstract remains on detail. The new detail section
links each keyword to publication-filtered search and explicitly describes its
source rather than presenting inferred topics. Unified search still has twelve
entity categories; keywords are metadata, not additional entities.

## Explicit variant literature assertions

`PublicationVariant` references an existing publication and variant with restrictive
foreign keys, unique publication/variant/source/source-record identity, an explicit
`curated` or `structured_metadata` evidence kind, and the existing relationship
provenance fields. It follows the same contract as gene/protein/disease literature
links. Duplicate source assertions return 409 and missing targets return 404.

Protected `POST /api/v1/publications/{id}/links/variant` uses the existing link payload
and fail-closed administrator dependency. Relationship views expose the assertion in
both directions; graph traversal/filters add `publication_variant`. Its predicate is
`mentions`, not causes/pathogenicity/treatment evidence. A mention is not a clinical
or causal conclusion. No variant link is extracted from words, keywords or rsIDs in
an abstract. The PubMed importer continues to create only explicit NCBI `pubmed_gene`
links to genes already stored locally.

## Migration and verification

Migration `20261112_0014` adds the keyword column with an empty array default and
creates the sourced variant-link table, its indexes, evidence checks and constraints.
Existing records, partial dates and citation identity remain intact. The downgrade
refuses when keyword or variant-link data would be discarded; operational rollback
retains the additive schema and new migration service while restoring old application
images. Never reset or downgrade the live database as a rollback shortcut.

Validation covers metadata parsing and bounds, idempotent refresh, Unicode keyword
matching in SQLite/PostgreSQL, matched-field display, protected link creation,
duplicates/targets, bidirectional evidence and graph traversal. Original suites,
fresh migrations, restored-live upgrades, model comparison, Ruff/mypy and frontend
test/format/lint/type/build checks also run. Before rollout, retain the private
checksum-verified backup and old images, and test old application reads on the
upgraded clone before touching the public deployment.

## Bounded real-data validation

Two real PubMed citation imports were first tested on an upgraded copy of the live
database through the existing adapter and private monitored NCBI contact:
[PMID 40524430](https://pubmed.ncbi.nlm.nih.gov/40524430/) and
[PMID 39688918](https://pubmed.ncbi.nlm.nih.gov/39688918/). Each source record supplied
five stored keywords. Their structured ELink responses created zero local gene links;
none were inferred from their titles. No variant records or variant links were
created. This is a bounded starter set, not a comprehensive or automatically
scheduled literature feed. Public loading is recorded separately in DATA_STATUS.md.

Release checks passed 208 backend and 52 frontend tests plus migration/model, lint,
formatting, typing and build checks. The retained 0.16 application successfully
read the upgraded clone, including the new real citations. Existing gene/protein/
transcript/ontology counts were preserved.

Variant-link creation locks the target variant using the same row lock as identity
updates. Once sourced placements or variant citations exist, application updates
cannot change the variant's rsID, HGVS or organism. Descriptive changes remain
supported. Direct SQL bypasses these application guards. The complete PostgreSQL
suite was rerun after adding this citation identity protection.

The deployed 0.17 application was verified over public HTTPS with both real
citations and their keyword lists, keyword-only result context, variant-relation
graph filters, the new SPA bundle and blocked public writes. The active backend
includes the citation identity guard and target row lock; the full suite passed
after that change. Migration head is 20261112_0014.
