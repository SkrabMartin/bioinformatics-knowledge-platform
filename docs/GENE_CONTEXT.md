# Gene context — release 0.9.0

This release advances the biological model in **Phase 2 of the owner's long-term
roadmap**. It is not a claim that long-term phases 0–9 have all been completed.
The earlier numbered implementation milestones remain historical records.

## Source and identity rules

NCBI Gene summary OtherAliases provides alternate names. GenomicInfo entries
provide ChrAccVer and zero-based ChrStart/ChrStop. These semantics are described
in the [NCBI Gene docsum fields](https://www.ncbi.nlm.nih.gov/books/NBK3841/table/EntrezGene.T.the_name_attributes_of_gene/)
and the [NCBI Gene FAQ](https://www.ncbi.nlm.nih.gov/books/NBK3840/).
The adapter uses only explicit fields, converting start/stop to one-based inclusive
min/max positions while retaining strand and sequence accession.

A sequence accession is not an assembly accession. This release does not infer
GRCh37/GRCh38, normalize chromosomes, resolve assembly aliases, fetch transcripts,
or invent missing placements. Legacy coordinate fields remain unchanged in schema
and API; older manual records may not specify their coordinate convention.

Aliases are source-scoped observations associated with a canonical gene. They are
not globally unique identifiers and never merge different gene records.
Gene NCBI/Ensembl identity fields and the existing symbol/taxonomy route remain
compatible. The symbol route still expects a canonical symbol; searching an alias
returns links using the canonical symbol and organism taxonomy.

## Persistence and refresh

Additive migration 20261107_0008 creates gene_aliases and gene_genomic_locations,
with restrictive foreign keys, source-scoped uniqueness and SQL coordinate checks.
There is no historical-data backfill: existing rows are not labeled with invented
sequence or assembly identities.

Both the CLI import and queued imports use the same existing GeneIngestionService.
It locks existing genes and atomically stores normalized gene context together
with the entity. The adapter accepts at most 100 alias values and 100 placements
per response. Up to 500 retained aliases and 500 placements per gene/source are
allowed; overflow aborts/rolls back the import rather than truncating silently.
This service bound does not apply to unsupported direct SQL writers.

Reimport deduplicates observations and refreshes their retrieval time. New context
changes an otherwise unchanged import result to updated.
Missing aliases/placements are not automatically erased; older observations may
remain and do not establish current preferred assembly or current source membership.
This is not an immutable per-release source snapshot or a retirement history.

A requested taxonomy mismatch fails before persistence. Existing gene organisms
cannot be changed during import; API organism edits are also rejected when these
source-backed annotations exist, preserving their biological identity context.
Conflicting imports fail rather than reconcile identities automatically.

## Search and API

GET /api/v1/genes/by-symbol/{symbol}?taxonomy_id=… adds arrays aliases and
genomic_locations, each with record provenance, source identifier, URL and retrieval
time. Existing list and numeric-ID gene responses retain their prior shape.
No new public write endpoint is introduced.

Unified search and suggestions now include gene alias partial/exact matches.
Correlated EXISTS queries avoid duplicate gene results and preserve counts/pagination
when multiple aliases match. Canonical identifiers/symbols rank above an exact alias.
Mixed terms can match alias plus ordinary gene fields. LIKE wildcard characters
are escaped. The original PostgreSQL gene full-text index expression is unchanged;
aliases have a trigram GIN index and a gene foreign-key index.

Alias matches include an alias matched-field label. The source on a search result
remains the gene record source; alias-specific provenance is on the detail response.
This is not an ontology-wide synonym engine or fuzzy cross-provider identity
resolution. Query plans on large biological corpora remain unbenchmarked.

## UI and operations

Gene detail shows source-reported aliases and reference sequence placements.
Empty arrays produce honest empty states. Reference coordinates and their
one-based convention are distinguished from the legacy location summary.
Earlier observations and unknown assembly identity are explicitly identified.

No real external records, fixture rows or scheduled jobs are created automatically.
Real imports remain explicit CLI/queue operations with the existing contact/rate
requirements. The public site remains read-only.

Before deploying to existing data: make a private pg_dump, verify a restore in
disposable PostgreSQL, retain prior runtime images, then use the existing VPS
scripts/bkp-preview.sh build/up procedure. Older 0.8.0 code is compatible with the
new independent tables, so application rollback does not need schema downgrade.
Never delete volumes or run a destructive downgrade as a routine rollback.

## Verification

95 backend tests passed, including all existing phases and fresh PostgreSQL 17
replay of all eight migrations with no Alembic model/schema differences.
Tests cover source field normalization, reverse strand and zero-coordinate
conversion, malformed metadata, replay/missing observations, transaction rollback,
taxonomy protection, shared aliases, ranking/pagination and real SQL constraints.

33 frontend tests, ESLint, Prettier, TypeScript and the production build passed.
Synthetic source responses are used only in tests; no synthetic scientific records
are inserted into the public instance.
