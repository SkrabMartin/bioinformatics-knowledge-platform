# Data quality review — 0.12.0

This is an initial, read-only part of long-term roadmap Phase 5. It reviews stored
metadata for genes, proteins, transcripts and gene identifier assertions. It does
not certify biological correctness, detect all errors, compare live providers,
repair data, ingest data or create a scientific quality score.

## API and interface

`GET /api/v1/data-quality?refresh_after_days=90` returns ten fixed checks with
assessed/affected counts, an explanation, severity and at most five stable,
ID-ordered examples each. The interval accepts 1–3650 days. `/data-quality` exposes
this review, interval selection, source-scope limitations and record links.
Gene links preserve organism taxonomy; a missing taxonomy produces a plain label
instead of accidentally opening a human record with the same symbol.

Checks cover:

- Missing source name, source record identifier, source URL or retrieval timestamp
  separately for genes, proteins and transcripts (metadata warnings).
- Retrieval older than the requested interval for those three entities (information
  for refresh planning). Missing retrieval timestamps are counted in the metadata
  check; retrieval age does not prove that biology or the upstream source is outdated.
- Genes lacking a source-evidenced primary Ensembl identity (coverage information).
- Genes with a registered primary identifier but no evidence (metadata warning).
- Genes whose registered identifier differs from its corresponding legacy field,
  including a missing legacy value (consistency error requiring human review).
- Linked proteins whose stored organism ID differs from the gene's organism ID
  (consistency error). Unlinked proteins are not assumed erroneous.

`development_fixture` records are excluded. Gene registry assertions and transcripts
under fixture genes are excluded too; provider labels otherwise remain unchanged.
Assessed counts are rule-specific: organism consistency assesses linked, non-fixture
protein/gene pairs. Counts overlap across checks and must not be summed as unique
records. Examples are a bounded sample, not a complete findings export.

## Operation and limits

The review uses SQL counts and bounded examples rather than loading entire tables.
It has a five-second application time budget and PostgreSQL statement deadlines;
a timeout returns a safe 503 `quality_timeout`, never a fabricated empty report.
The budget covers database queries, not a strict end-to-end HTTP SLA. The operation
uses a session without data writes or commits and does not call external providers.
No database migration is needed for this release.

Start/end times bound the review. Under concurrent imports, its multiple queries
can observe changes; it is not an immutable or transaction-wide historical snapshot.
The present release does not assess diseases, variants, ontology assertions,
publications, source URL validity, biological truth, source payload changes or all
possible duplicate/conflict types. Existing constraints handle some duplicates;
this page does not claim a general duplicate-detection system.

## Release checks and deployment

Run the full backend suite on an isolated migrated PostgreSQL database, schema/model
comparison, Ruff and strict mypy; run frontend tests, formatting, lint, typecheck
and build. Tests include fixture exclusion, exact counts and sample limits, refresh
intervals, absent timestamps/taxonomy, conflicting registry projections, orphaned
registry evidence, organism mismatches and time-budget failure.

Before updating the existing VPS/Compose application, retain its image IDs as
rollback tags and take a private custom-format PostgreSQL backup. Restore and
compare counts, then run the new read-only report on that isolated copy. After
building, update through the established VPS wrapper and verify public HTTPS,
SPA routing, catalogue counts, report JSON and blocked write methods. Returning
to the previous application images does not require a database downgrade.

Release validation passed 151 backend tests against isolated PostgreSQL and 41
frontend tests plus all checks above. The restored starter database retained three
genes, three proteins, 128 transcripts and six identities with six source assertions.
The ten checks found no affected records in that clone; this is not a statement
about unassessed entities or overall scientific correctness.

The deployed 0.12 application was subsequently verified over public HTTPS: the
review returned ten checks with the expected assessed counts, interval validation
worked, the SPA bundle contained the new page/version and original catalogue
counts were retained. The existing public proxy continued to block write methods.
