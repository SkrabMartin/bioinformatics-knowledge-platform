# Transcript interval browsing — 0.24.0

This is an initial Phase 17 Genomics Toolkit increment. It queries existing local
transcript span annotations by exact organism, assembly and sequence-region name.
It is not a full genome browser, sequence/reference service, exon/coding annotation
engine, variant effect predictor or FASTA/FASTQ/VCF/BED/GFF file importer.

## Coordinate contract

`GET /api/v1/genomics/transcript-overlaps` takes explicit `taxonomy_id`,
`assembly_name`, `sequence_region`, `start` and `end`. `coordinate_system` is
`one_based_closed` by default or `zero_based_half_open`; optional `strand` filters
stored '+'/'-' annotations. `page` is 1–1,000,000 and `page_size` is 1–100.

For a 1-based closed interval [s,e], require 1 <= s <= e. For a 0-based half-open
interval [s,e), require 0 <= s < e and normalize to [s+1,e]. Hence [100,200] and
[99,200) name the same reference span. Empty half-open intervals are rejected.
Every displayed transcript/query/overlap coordinate is **1-based closed**.
Input positions are at most 10^12, safely representable as browser integers; query
length is at most 10,000,000 reference bases.

These conventions are consistent with the [UCSC BED coordinate definition](https://genome.ucsc.edu/FAQ/FAQformat.html#format1)
and the distinction documented for [Ensembl BED inputs](https://www.ensembl.org/info/website/upload/bed.html).
BKP does not parse BED files here. Its exact-name matching is deliberately stricter
than source tools which may accept chromosome aliases.

Overlap uses `transcript.start <= query.end AND transcript.end >= query.start`
after normalization. The intersecting span is [max(starts),min(ends)], with length
end-start+1. Reference-axis positions remain ascending on both strands; the strand
filter never reverses or reinterprets coordinates.

## Reference identity and scientific interpretation

Organism taxonomy, assembly label and sequence region must match the stored data
exactly and case sensitively. GRCh37/GRCh38 are not combined; 17/chr17 are not
aliases. No assembly accession reconciliation, contig membership/length check or
coordinate liftover is attempted. An unknown reference label yields no local matches,
not evidence that the reference or biology does not exist.

The results overlap **whole transcript spans**, including intronic portions.
Reference-base overlap is not RNA sequence length, exon overlap, expression or
functional consequence. Counts are transcript records, not unique genes. Different
transcripts can overlap the same region. Source releases can differ among stored
records; the response does not assert one consistent reference snapshot.

Returned records retain observed transcript/version, gene links, strand, assembly,
region, source/release, source identifier/URL and retrieval/update timestamps. A
query envelope retains original coordinate system and normalized bounds, method
`local_transcript_span_overlap_v1`, application version and observation time.

## Query/runtime behavior

Migration 20261114_0018 adds the nonunique B-tree index ix_transcripts_interval on
(assembly_name, sequence_region, start_position, end_position). No rows or identity
constraints are modified. The index supports exact reference-prefix filtering;
it is not a claim of optimal interval indexing for every future dataset size.
Downgrade removes only this index and does not discard source records.

Two explicit database queries count and page matches, ordered by transcript start,
end, accession and local ID. No relationship lazy loading or upstream call occurs.
A three-second application/remaining statement budget returns safe
`genomic_interval_timeout` rather than fabricated empty data. Returned rows are
bounded by page size; count/index scan costs are not constant. Counts/pages may
drift during concurrent imports. No transcript index is rebuilt in web requests.

## Frontend

`/genomics/intervals` retains the flat shared controls/tables. Submission is
explicit and old results are labeled as the last submitted interval. Changing
coordinate mode reinterprets entered numbers; it does not edit them automatically.

The example button reads one stored transcript through the existing catalogue
API, fills its exact source reference/taxonomy and up to its first 1,000 reference
bases, and waits for submission. It guesses no reference when no suitable record
exists. Pagination preserves the submitted interval. Empty pages are distinguished
from no matching interval coverage. Inputs are GET request parameters and can
appear in request/proxy logs; no file uploads or saved analysis history exist.

## Verification and operations

Tests cover first-base conversion, inclusive endpoints, half-open exclusions,
strand/reference/organism separation, exact region strings, pagination, invalid
or excessive intervals, source context, flat API parameters and read-only behavior.
PostgreSQL checks exercise actual overlap queries, index-plan eligibility and
slow-query cancellation with transaction setting cleanup. Frontend tests cover
stored examples, explicit submission, coordinate mode, empty coverage and missing
source examples.

Before rollout, restore a fresh private backup, apply the index migration, compare
original counts and verify a real stored transcript in both coordinate systems.
Retain previous backend/frontend images; their catalogue reads remain compatible
with the extra index. Do not reset a database or downgrade biological data.
