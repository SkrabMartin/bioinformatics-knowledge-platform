# Dataset queue and public import activity — 0.21.0

This increment advances long-term Phase 14 using the existing durable PostgreSQL
queue and singleton worker. It retains the flat research frontend introduced in
commit def13d2 and reuses its shared tables, navigation and loading/empty states.
No Redis/Celery, distributed execution, recurring schedule or user accounts are added.

## Dataset jobs

The protected import-job API and `enqueue-import` CLI now accept `entity_type:
"dataset"`, 1–100 explicit GEO Series accessions matching `GSE[1-9][0-9]{0,15}`.
Outer whitespace is trimmed and duplicate identifiers are removed in order.
Taxonomy filters are rejected for datasets. Protein/gene/publication contracts
remain unchanged. Idempotency keys retain the existing exact-batch semantics.

```sh
python -m app.cli enqueue-import dataset GSE10072 --idempotency-key geo-series-review-1
python -m app.cli import-worker --once
```

These commands create/process work only when explicitly invoked. `--once` handles
one ready queue item, which may belong to an older job; it does not target a
particular accession. Starting the web application does not run a worker.

The provider dispatch reuses GeoSeriesAdapter and DatasetService.refresh rules:
one public metadata self-record, no experimental files/contact fields, strict
accession/source validation, no provider-date regression and no duplicate dataset.
No automatic publication import or citation resolution is performed. Unknown
provider kinds fail closed rather than falling back to the protein adapter.

Queue retries own the attempt budget; the shared HTTP transport performs one
attempt per item attempt and retains request pacing. Rate-limit/unavailable errors
can retry within the bounded budget. Source conflicts become safe terminal
`ingestion_conflict` codes, without storing provider bodies or exception text.
Existing cancellation and singleton crash-replay behavior also apply to datasets.

## Read-only public activity

`GET /api/v1/import-status` returns four fixed rows (gene, protein, publication,
dataset), job/item counts by state, last stored queue activity and observation time.
`/import-status` renders shared tables with a manual refresh button.

One SQL grouped UNION statement selects counts and timestamps only. It never
selects job UUIDs, idempotency keys, accessions, results, errors, credentials or
private configuration. Individual job endpoints remain protected by require_admin;
no administrator credential is collected by the public frontend.

Counts cover historical and active queue records, not biological entity totals.
Direct CLI single-record imports are outside queue history. Zero jobs does not
mean zero imported biological records. Last queue activity is not data freshness.
`worker_status` is deliberately `unknown`: a persisted running item can survive
a crash, and no heartbeat/process check is implemented. Refresh performs a GET;
it does not start imports, reconnect a worker or enable scheduling.

## Migration and operation

Migration 20261114_0017 widens the existing import_jobs entity-type check constraint.
It deletes no records and creates no fictitious jobs. Downgrade refuses while
any dataset jobs exist, including completed/cancelled history.

Workers older than 0.21 do not support dataset jobs. Stop old workers before
upgrading and start only the new worker image when dataset work is enabled.
Do not roll back a worker to an older image while dataset jobs remain. A retained
old application image can still read the biological catalogues on the widened
schema, but its protected job API cannot deserialize dataset jobs. Retain the
new queue-aware backend for queue operations; never delete history to force rollback.

The current deployment's optional imports worker is not automatically enabled.
If a worker is already running, deployment must explicitly update that service
before accepting dataset work. Public writes remain blocked at the preview proxy.
This release does not enqueue live jobs by itself.

## Verification

Tests exercise dataset validation/idempotence, actual provider dispatch with
synthetic SOFT responses, terminal source conflicts, bounded unavailable retries,
privacy of aggregated status, cancellation, protected job endpoints and PostgreSQL
constraint/JSON/date aggregation. Frontend tests cover honest empty states,
manual GET refresh and network failure without invented counts.

Before deployment, restore the live backup, migrate the clone and check model
comparison, original table counts and existing catalogue/search/graph reads. A
bounded real GEO queue refresh may be tested on the clone only. Keep secrets and
backup artifacts private, outside Git. See IMPORT_JOBS.md and DATASETS.md.
