# Phase 8: tracked imports

BKP 0.8.0 implements the next phase explicitly identified by the README roadmap:
background processing, tracked import jobs, retries and bounded batches.
The original single-record CLI commands and entity APIs remain compatible.

## Scope and architecture

An administrator submits 1–100 explicit identifiers for one provider/entity type:
NCBI Gene symbols with an explicit taxonomy ID, UniProt accessions, or PubMed IDs.
Inputs are validated, whitespace trimmed and exact duplicates removed; identifiers
are never interpreted as arbitrary provider query expressions or URLs.
This is a bounded identifier queue, not a bulk download, provider search or scheduler.
Syntactic validation does not establish biological validity.

PostgreSQL stores jobs and their individual items in the additive
`20261107_0007` migration. It does not modify existing biological tables or import
fixtures. One optional worker uses the existing normalization/ingestion services;
record and relationship provenance retain their current semantics.

A PostgreSQL session advisory lock admits one queue worker per database. The same
connection owns the lock, metadata writes and biological imports across commits.
Database failures abort the worker rather than silently resuming without the lock.
No Redis, Celery or web-process background thread is required. Independent legacy
CLI imports do not participate in this worker lock.

Item states: pending → running → succeeded / failed / retry_wait.
Cancellation turns unstarted items into cancelled. An in-flight import may finish
and commit: cancellation does not undo scientific records. The job is then
cancelled, with separate counts showing any successful/failed earlier items.
Other terminal job states are succeeded and completed_with_errors.

After a crash, the next lock owner recovers running items within the original
attempt budget. Delivery is **at least once**: a crash after entity commit but
before progress commit can repeat an import. Existing stable identity checks and
idempotent ingestion prevent duplicate entities in the supported replay path.
A crash on the last allowed attempt can leave a failed item whose entity was
already saved; inspect it before explicitly submitting another job.
There is no claim of exactly-once execution, batch-wide atomicity or automatic
reconciliation of source records that change between attempts.

## Retries and provider limits

Each item allows 1–5 attempts (default 3). Only upstream unavailability and rate
limiting are retried. Missing/invalid records, configuration errors and identity
conflicts fail individually; other batch records continue. Unknown application
errors fail with a generic code. Database errors terminate the worker.

Queue imports use one HTTP transport attempt per item attempt, avoiding multiplied
retry loops. Backoff starts at 60 seconds, doubles and caps at one hour.
Numeric Retry-After on rate limits can extend the delay up to 24 hours; HTTP-date
Retry-After is not implemented. Attempt counts measure record attempts, not HTTP
calls: a citation or gene can require several provider requests.

A shared transport spaces every worker request at least 0.4 seconds apart by
default (minimum configurable interval 0.34 seconds), including internal adapter
requests. This follows the conservative non-key NCBI request-rate boundary:
[NCBI E-utilities guidelines](https://eutilities.github.io/site/API_Key/usageandkey/).
This limiter covers this worker only; other processes/hosts sharing the same
outbound IP must be coordinated separately. Configure a real monitored
`BKP_NCBI_EMAIL` before NCBI jobs. No contact identity is invented.

## CLI

From backend with the root virtual environment activated and the appropriate
`BKP_DATABASE_URL` set privately:

```bash
python -m app.cli enqueue-import gene TP53 BRCA1 --taxonomy-id 9606 --idempotency-key my-gene-batch
python -m app.cli enqueue-import protein P04637
python -m app.cli enqueue-import publication 123456
python -m app.cli import-job JOB_UUID
python -m app.cli cancel-import-job JOB_UUID
python -m app.cli import-worker --once
python -m app.cli import-worker
```

These enqueue examples request real provider imports when a worker runs.
Do not execute them just to seed a preview. Tests use synthetic provider responses
only in disposable test databases. The running public preview is kept free of
automatic imports.

Idempotency keys are optional, unique, case-sensitive strings up to 128 characters.
An identical normalized request with the same key returns the existing job;
reusing a key for different identifiers/options returns a conflict. Identifier
order is part of the request. A new key or no key intentionally creates another job.

## Compose and the public site

Both development and preview have an opt-in `imports` worker profile.
The default startup does not start a worker. Existing queued jobs stay durable
while it is stopped. For the active site use the VPS wrapper to preserve autostart:

```bash
/home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh --profile imports up -d worker
/home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh stop worker
```

The worker is not enabled for VM autostart by this release. SIGTERM/SIGINT requests
a graceful stop after the current item; Compose waits 60 seconds before killing.
Forced termination is recovered by the next worker within the attempt budget.
Provider timeouts are per network operation, not a strict whole-record deadline.

To queue or inspect from the active backend container, for example:

```bash
/home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh exec -T backend python -m app.cli import-job JOB_UUID
```

Worker and backend have no public host ports. Public nginx/Caddy continue to allow
only GET/HEAD on the API. All job API endpoints, including reads, require the
existing server-side administrator bearer token and fail closed without one.
The preview intentionally leaves this token empty and does not open an admin UI.
Use the host CLI or a separately secured administrative channel; never put a token
in frontend variables or remove the public proxy's method restrictions.

Endpoints under `/api/v1/import-jobs`:
POST create, GET paginated list, GET `/{uuid}`, GET `/{uuid}/items` (page size ≤100),
POST `/{uuid}/cancel`. Responses expose safe codes and structured entity results,
not raw upstream payloads, exception messages, database URLs or credentials.
HTTP client access/debug logging is suppressed by the worker CLI.

Configuration: `BKP_IMPORT_REQUEST_INTERVAL_SECONDS=0.4`,
`BKP_IMPORT_RETRY_SECONDS=60`, `BKP_IMPORT_POLL_SECONDS=2`.
CLI access relies on host/container authorization; it does not use the HTTP token.

## Verification and limitations

78 backend tests passed with PostgreSQL 17, including singleton exclusion, crash
after biological commit, idempotent replay, cancellation from another connection,
all three provider dispatch paths, durable delays, rate-limit Retry-After,
authorization, invalid batches and safe error storage. Seven migrations replayed
on a fresh disposable database; Alembic check found no schema differences.
Frontend checks and production build cover the updated phase label/About text.

This phase has no cron scheduling, distributed worker pool, automatic bulk
discovery, retention/purge, arbitrary automatic retries of terminal failures,
per-attempt audit table, raw payload archive or enrichment engine.
History is the current state/result, attempts and safe last error per item.
Queue length/history retention and list counts are not production-scale benchmarked.
The owner’s [long-term roadmap](ROADMAP.md) now supplies the broader direction; its phase numbering differs from this historical milestone.
