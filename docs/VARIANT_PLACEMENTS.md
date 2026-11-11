# Assembly-aware variant placements — 0.15.0

This is an initial part of long-term roadmap Phase 8. It adds source-supplied
literal sequence replacements to existing variants while preserving legacy rsID,
HGVS, organism and relationship APIs. It does not implement all variant types,
clinical interpretation, genome browsing or automatic variant import.

## Representation contract

Each observation belongs to an existing variant and requires an assembly name,
versioned sequence accession, positive taxonomy ID, explicit
`coordinate_system: one_based_closed`, explicit `strand: +`, start/end positions,
REF and ALT strings and full source metadata. An optional assembly accession must
match a versioned NCBI `GCA_`/`GCF_` identifier. A sequence-region label is optional.
Names and accessions are retained as supplied, with surrounding label whitespace
removed. No assembly aliases or chromosome labels are resolved automatically.

Both alleles must be nonempty literal A/C/G/T/N strings, at most 1000 bases; lowercase
is converted to uppercase. REF and ALT must differ. Positions are strict positive
integers within signed BIGINT range. The closed interval length must equal REF
length. Coordinates span the entire supplied reference allele, including any padding.

This contract draws on literal replacement conventions described in the
[VCF specification](https://samtools.github.io/hts-specs/VCFv4.3.pdf), but it is not a
VCF parser or full VCF validator. The optional assembly-accession shape follows
[NCBI assembly versioning](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/policies-annotation/genome-processing/version-status/).
Neither source establishes that an administrator-supplied placement is biologically
correct.

Symbolic alleles, breakends, empty alleles, multi-ALT strings, zero-based intervals,
reverse-strand representations, liftover, left alignment, allele trimming and
reference-sequence validation are unsupported. A different-length REF/ALT can be a
source-supplied small-indel or complex literal replacement; no event class, padding
correctness or minimal representation is inferred.

The server checks the reported taxonomy against the variant's current organism,
under row locks. It does not verify that the accession exists, that its sequence
belongs to the named assembly, that REF matches a reference FASTA, or that the
placement corresponds to the parent's rsID/HGVS. The detail panel makes these limits
explicit. No clinical significance, frequency, gene effect or disease assertion is
created from coordinates or alleles.

## Source observations and API

`GET /api/v1/variants/{id}/placements?page=1&page_size=20` lists observations for an
existing variant, with at most 100 records per page; missing parent returns 404.
`POST` on the same path uses the existing fail-closed admin bearer dependency.
Creation requires a source name, source record ID, release, HTTP(S) source URL and
explicit timezone-aware retrieval timestamp. Public proxy writes remain blocked.

Observations are immutable through the API. An internal SHA-256 key covers assembly
name/accession, sequence accession, taxonomy, coordinate system, strand, coordinates
and uppercased alleles. This is a bounded storage deduplication key, not a biological
variant identifier or a claim of normalized biological equivalence. Sequence-region
display aliases are not part of the key. Names are not canonicalized across sources.

The database prevents duplicate assertions for the same variant, representation key,
source, source record and source release. Duplicate creation returns 409. Distinct
representations, assemblies, sources and releases remain separate observations;
they are not merged into an inferred consensus. No large allele strings are placed
in the uniqueness index.

Once placements exist, application updates cannot change the parent variant's rsID,
HGVS or organism. Changing its organism's taxonomy is also blocked. Descriptive
updates remain supported. These guards use the same parent/organism locks as
placement creation; direct SQL bypasses application guards and must be managed
separately. The foreign key restricts deletion of referenced variants.

## Interface, scope and migration

Variant detail now includes a paginated Genomic placements panel with assembly and
sequence labels, explicit coordinate convention, literal alleles, taxonomy, source
release, retrieval time and provider link. An empty panel does not derive positions
from rsID/HGVS. No new search entity is introduced: unified search retains eleven
categories and searches variants by its documented existing fields. The quality
review's scope is unchanged; it is not a placement-quality report.

Additive migration `20261111_0012` creates only `variant_placements`, its foreign key,
source/parent indexes and coordinate/allele/uniqueness constraints. Existing rows are
not backfilled. New placement collections start empty; no real or synthetic variant
records are inserted into the public database by deployment.

## Verification and rollback

Tests cover strict coordinates, reference spans, literal-allele limits, source
requirements, taxonomy mismatch, duplicates, retained releases/assemblies, pagination,
parent identity/taxonomy guards and PostgreSQL constraints. A PostgreSQL test stores
1000-base alleles to check bounded deduplication indexing and exercises restrictive
foreign keys. Frontend tests preserve coordinate interpretation and honest empty
states. Existing API and biological data checks also run.

Before rollout, restore a new private live backup, compare data counts and upgrade
both a fresh test database and the restored copy. Retain previous backend/frontend
images and verify that the previous application can read the upgraded clone. Update
through the established VPS/Compose wrapper and verify public HTTPS and blocked
writes. Roll back only application images while retaining the new migration service
and additive schema; the older migration image cannot recognize revision
20261111_0012. Never reset or downgrade the live database as a rollback shortcut.

Release validation passed 195 backend and 48 frontend tests plus migration/model,
lint, formatting, typing and build checks. The upgraded live backup retained the
original three genes, three proteins, 128 transcripts and six evidenced identities,
as well as the existing empty disease/variant/phenotype collections. Its new
placement table was empty. The previous 0.14 backend was smoke-tested against that
upgraded clone and retained the original TP53 search results.

The deployed 0.15 application passed public HTTPS checks for placement route
validation and missing-parent responses, the new SPA bundle, blocked public writes,
existing search/quality and original catalogue totals. The active database head is
20261111_0012 and the new placement table contains zero observations.
