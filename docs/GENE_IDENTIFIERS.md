# Source-backed gene identifiers (0.11.0)

The registry distinguishes `ncbi_gene` from `ensembl_gene`. Each gene has at most
one primary identity in each supported namespace, and each namespace/accession
belongs to only one gene. Migration 20261111_0010 adds identity and evidence tables;
it neither deletes existing data nor retroactively treats legacy columns as proof.

NCBI gene imports record their direct identifier evidence. UniProt protein imports
can record explicit GeneID and Ensembl GeneId references only when the NCBI ID
resolves to an existing gene with a matching organism. An unknown explicit NCBI ID
never falls back to a matching symbol. Symbol-only matches cannot create identifier
evidence. Conflicting identities abort the record transaction; no genes are merged.
The legacy Ensembl column is populated only after these checks, enabling the
existing explicit Ensembl transcript import command.

Evidence retains the source record, retrieval time, source URL, reported accession
(including an observed Ensembl version suffix), and optional UniProt entry version.
A UniProt entry version is not an Ensembl release. Each identity retains up to 200
evidence assertions; overflow fails atomically. This is a primary-identifier registry,
not a historical mapping or automatic identifier retirement service.

`GET /api/v1/genes/by-identifier/{namespace}/{accession}` resolves registry evidence.
Unversioned IDs return the current gene; versioned Ensembl IDs require an exact
observed reported accession. Unknown IDs/versions return 404, invalid formats or
namespaces return 422. A version match does not reconstruct a historical gene.
Gene detail exposes `external_identifiers` and nested evidence; numeric gene APIs
and list contracts remain compatible. The frontend displays these source assertions.

Application updates protect registered identities and organism assignments. Direct
SQL operations bypass application guards and require separate operator discipline.
There is no public mutation endpoint for the registry and no scheduled refresh.

## Ensembl interoperability

The species adapter accepts positive integer taxonomy IDs supplied as integers or
strict decimal strings, as observed in live `/info/species` responses. Invalid types
remain errors. Requests use the documentation-style literal JSON content-type query
and `expand=1` lookup. This request shape succeeded during live validation where a
percent-encoded media-type query had timed out; availability still depends on Ensembl.
Transcript ingestion continues to validate parent, organism, assembly and source
release, with atomic persistence and no inferred transcript annotations.

## Verification and rollback

Backend validation includes namespace collisions, conflicting mappings, atomic
rollback, bounded evidence, observed-version resolution, taxon parsing and actual
PostgreSQL uniqueness. The full PostgreSQL suite passed 142 tests; migration/model
comparison, Ruff and strict mypy passed. Frontend checks cover provenance and empty
states alongside the existing suite.

Before deployment, a private PostgreSQL custom-format backup was restored into an
isolated database, upgraded and compared with original record counts. Retain the
private deployment manifest, dump checksum and tagged 0.10 backend/frontend images.
Rollback runs those images with the additive schema retained; do not downgrade or
reset the live database. Restoring the pre-release dump would discard later imports
and requires explicit operator approval. Existing VPS/Compose deployment is used;
no SFTP transfer or public infrastructure configuration is required.
