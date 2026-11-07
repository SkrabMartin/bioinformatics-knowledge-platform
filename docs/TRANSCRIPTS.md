# Transcripts — release 0.10.0

This increment advances long-term roadmap Phase 2 (biological model) and a bounded
part of Phase 3 (external adapters). It does not claim completion of either phase.

## Delivered

- A first-class Transcript model linked to an existing Gene, with Ensembl stable
  ID, optional transcript version/name/biotype, explicit assembly name, reference
  region, one-based inclusive coordinates, strand, release and retrieval provenance.
- A bounded Ensembl adapter using expanded lookup/id and info/species.
  References: https://rest.ensembl.org/documentation/info/lookup and
  https://rest.ensembl.org/documentation/info/species.
- Atomic, idempotent CLI import for one already mapped gene; paginated read APIs,
  a /transcripts browser, transcript detail and observed transcripts on gene detail.
- Additive migration 20261107_0009. Existing gene/list/ID and queued-import
  contracts remain compatible.

## Import

The local gene must already have the correct explicit Ensembl gene ID and matching
NCBI taxonomy ID. The importer never resolves identity by gene name, creates a
partial gene or silently changes a transcript's parent.

From the active host, with secrets already in the private Compose configuration:

    /home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh exec -T backend python -m app.cli import-transcripts ENSEMBL_GENE_ID

Use a versionless Ensembl gene ID. BKP_ENSEMBL_BASE_URL defaults to
https://rest.ensembl.org and can point to an appropriate source server.
This command is not a new queued entity type; the existing worker still processes
gene/protein/publication items only. There is no automatic transcript import.

The adapter requires explicit source Parent/species/assembly/region/strand agreement,
a unique matching species metadata row with numeric taxon/release, and transcript
coordinates contained in the provider gene span. Duplicate, missing, malformed,
oversized and contradictory annotations fail closed. A batch may explicitly contain
zero transcripts. At most 200 transcripts per source response are accepted; the
existing decompressed HTTP response cap is 2 MB. There is no silent truncation.

The source span and transcript coordinates are one-based inclusive; they are not
spliced sequence lengths. Assembly name is a source label, not an inferred assembly
accession or a complete normalized genome/assembly model. Exons, sequences,
translation links, canonical status and protein relationships are not synthesized.

## Persistence and compatibility

The gene is revalidated and locked after provider requests complete. Gene identity
or taxonomy mismatch aborts the import. Stable transcript identity is unique and
cannot be remapped to another local gene. Version/release regressions fail closed.
All annotations in a batch commit together or roll back. Retained observations are
limited to 500 per gene. An omitted transcript is not automatically deleted.

Each transcript stores the latest accepted observation; records from earlier
retrievals/releases may remain. The catalogue is not an immutable source snapshot
or proof of a complete current isoform set. Retrieval metadata does not make
different live HTTP responses a frozen provider snapshot.

API gene identity/organism changes are rejected while transcripts exist. Existing
gene ingestion also preserves transcript-linked Ensembl identity. Unsupported direct
SQL writers must respect the same service invariants.

Read APIs:
- GET /api/v1/transcripts with page, page_size <=100, gene_id and literal q filter.
- GET /api/v1/transcripts/by-ensembl/{stable_transcript_id}.
- Canonical gene detail adds a transcripts array; older list/numeric-ID responses
  keep their shape. Versioned transcript IDs can be filtered in the catalogue.
- Transcript search is scoped to the browser, not a new unified-search category.
  Transcript graph nodes/edges are not part of this increment.

There is no new HTTP write endpoint. The public read-only proxy remains in place.
The CLI uses local host authorization, request timeouts/retries and conservative
per-process pacing. Concurrent independent commands are not a distributed limiter.

## Verification and operational status

117 backend tests passed with disposable PostgreSQL 17, nine fresh migrations and
no Alembic model/schema differences. New contracts cover explicit source identity,
taxonomy, assembly, coordinates, malformed/oversized/duplicate batches, idempotency,
version regression, cross-gene rollback, gene edit protection, filtering/pagination
and real PostgreSQL checks. 36 frontend tests, lint/format/typing and build passed.

Live Ensembl metadata checks encountered an HTTP 500 and a timeout during this
session. The new adapter is covered with synthetic source responses in isolated
tests; no successful live Ensembl transcript import is claimed. An actual source
failure leaves local records unchanged. The separately imported NCBI/UniProt
starter data are described in DATA_STATUS.md.
