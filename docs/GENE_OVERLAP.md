# Gene set overlap — release 0.23.0

This begins long-term Phase 16 with a descriptive local gene-list comparison.
It requires no pathway/GO corpus, statistical library, external source request,
new dependency or database migration. It does not implement enrichment,
statistical significance or clinical interpretation.

## Input and exact identity

`GET /api/v1/analysis/gene-overlap` accepts repeated `left` and `right` identifiers,
1–50 per list, and an explicit `taxonomy_id`. A single `namespace` (default symbol)
applies to both lists: symbol, ncbi_gene or ensembl_gene. Each identifier is at
most 64 characters, whitespace trimmed and validated against its namespace.

Symbols use ASCII letters/digits, underscore, dot and hyphen, and are exact and
case sensitive. NCBI/Ensembl identifiers match the existing
canonical local identifier registry, filtered to the selected organism. Ensembl
input must be unversioned; no version stripping, alias matching, fuzzy correction,
text-to-gene extraction or orthology inference occurs. Identifiers absent from
that namespace/organism stay unresolved. Their absence from the starter catalogue
does not establish biological absence. No external lookup is triggered.

The implementation combines both lists in one indexed identity query and maps
back to the submitted lists. PostgreSQL applies a transaction-local three-second
statement timeout with safe `analysis_timeout` on cancellation. Input/output sizes
are bounded; this is not an end-to-end latency guarantee. No rows are written.

## Set mathematics and coverage

Whitespace-normalized duplicate inputs are removed before comparing distinct
resolved local gene IDs. Both raw token counts and duplicate counts remain in
the report. `matched_inputs` records each unique input's local gene ID, and each
list separately records unresolved inputs and its resolved gene count.

Let A and B be the sets of **resolved** genes:

- shared = A intersection B
- left_only = A minus B; right_only = B minus A
- union = A union B
- Jaccard index = size(shared) / size(union)

An empty union returns null/undefined, not an invented 0 or 1. If unresolved
inputs exist, the report is marked partial (`coverage_complete=false`). They
are excluded from every set size and Jaccard denominator, even if the same
unknown token appears in both lists. The index therefore describes resolved
local subsets, not necessarily the original biological lists. It is not a
p-value, confidence estimate, enrichment score or measure of causal relevance.

The public example compares TP53/BRCA1 with BRCA1/PINK1 in taxonomy 9606.
When all three local records are available, shared=BRCA1, union size=3 and
Jaccard=1/3. This is a mathematical identity comparison, not an inferred
biological association among those genes.

## Report and provenance

The JSON report contains normalized inputs, exact input mappings, unresolved
values, metrics and ordered shared/unique gene records. Each record retains its
symbol/name, source identifier/URL, retrieval/update timestamps, resolved input
and the registry record ID when applicable. Full identifier assertion evidence
remains on linked gene detail pages; this report includes current gene provenance,
not all source assertion history.

Method `exact_local_gene_set_overlap_v1`, software version, taxonomy, namespace,
computation time and interpretation notes travel with the report. Gene records
are sorted by symbol and local ID. The saved report supports independently
recomputing the descriptive set counts from its resolved mappings. Re-running
input resolution later can differ as the catalogue changes: it is not an
immutable source snapshot, data-version archive or persisted analysis run.

## Frontend and request visibility

`/analysis/gene-overlap` reuses shared tables and existing controls, with the same
flat styling extended to textareas. An example button fills public human symbols
but does not run the analysis. Submit/refresh remains explicit. Editing the form
leaves a clearly labeled last-submitted result until resubmission; submitting the
same inputs again obtains a new report. JSON download contains the entire response
rather than only rounded display metrics. Failures preserve honest error states.

Identifiers can be separated by whitespace, comma or semicolon. The browser sends
GET query parameters; input lists can be present in request/proxy logs. The page
does not put the lists into its own browser address/history, upload a file, save
an analysis row or accept administrative credentials. Public read-only proxy
behavior remains intact. Users should choose appropriate public inputs for this
public preview; protected/private research workspaces are not implemented.

## Verification and deployment

Tests cover partial coverage, duplicate inputs, known set arithmetic, empty union,
case sensitivity, taxonomy isolation, exact registry identities, rejected versions,
source links/metadata, input limits, read-only API behavior and real PostgreSQL
query cancellation/setting cleanup. Frontend tests cover explicit submission,
repeated runs, partial/undefined output, bounded inputs and failed analyses.

Before rollout restore the live backup, verify the real three-gene example on
that clone, compare original table counts and retain previous application images.
No schema migration or biological import is needed; schema stays 20261114_0017.
