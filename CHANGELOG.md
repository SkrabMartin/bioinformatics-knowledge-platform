# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project intends to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once versioned application releases begin.

## [Unreleased]

### Changed

- Frontend restyled as a flat, high-contrast research interface: neutral background, 1px rules, square corners, one accent colour, and monospace for accessions, rsIDs, HGVS expressions, ontology IDs and coordinates. API contracts, routes, source notes and provenance are unchanged.
- Search is the first element of the home page; the marketing hero, entity cards and principles section were replaced by the search box, one stored gene record and a compact collections table.
- Datasets, phenotypes and transcripts use the shared data table. Filter forms, pagination and loading, error and empty states share one presentation. The primary navigation collapses behind a menu button on narrow screens.
- Graph nodes are distinguished by shape instead of colour; the root node and the selection use the accent colour. A small graph no longer opens at maximum zoom.

### Added

- Separate local staging Compose with a private PostgreSQL network, explicit migration service, static same-origin frontend, read-only API proxy, private configuration initializer and VPS/Tailscale handoff guide. No automatic fixtures.

### Security

- Restricted development HTTP port bindings to localhost and removed the database host port. Excluded all local environment variants from Docker build contexts.

### Fixed

- Made frontend Compose startup populate or repair its Linux `node_modules` volume from the committed pnpm lockfile before launching Vite.
- Excluded host `node_modules`, virtual environments, caches, build output, logs, and local environment secrets from Docker build contexts, preventing Windows dependency artifacts from overwriting container-installed packages.

## [0.23.0] - 2026-11-14

### Added

- Exact local gene-list overlap through a read-only bounded API and analysis page: intersection, left/right-only sets, resolved union and descriptive Jaccard index.
- Explicit organism/identifier namespaces, case-sensitive symbol/registry matching, duplicate counts, unresolved inputs and partial coverage. Empty resolved unions return an undefined index; no enrichment, p-value or biological relationship is inferred.
- Full JSON report downloads with inputs/mappings, method/software version and current gene source metadata. Existing controls/tables are retained; textarea styling extends the flat frontend.
- No schema change, biological import or additional dependency. A shared application version constant keeps analysis metadata and API version aligned.

### Verified

- 268 backend tests on isolated PostgreSQL, Ruff, strict mypy, fresh/restored migrations and Alembic model comparison passed; frontend passed 72 tests, formatting, lint, typecheck and production build.
- Restored real data returned BRCA1 as the shared gene, union size three and Jaccard 1/3 in symbol, NCBI and Ensembl namespaces. Original table counts and prior application reads were preserved. Schema remains 20261114_0017.

- Deployed HTTPS verified real overlap, registry resolution, empty/unknown handling, bounds, frontend assets and existing catalogue/graph/search/import activity. Checked database totals and schema stayed unchanged; public writes remain blocked.

## [0.22.0] - 2026-11-14

### Added

- Explicit similar-name hints for gene/protein names, organism names and publication titles through existing PostgreSQL pg_trgm indexes, with type filters, deduplication, source labels and bounded query time.
- Opt-in search-page control with conservative name-only validation, separate lexical scores and safe errors. Normal search counts, identifier lookup and autocomplete remain unchanged.
- No schema change, external search service, data import or additional dependency; the flat research frontend is retained.

### Verified

- The complete 254-test backend suite passed on isolated PostgreSQL, followed by all three PostgreSQL name-hint checks including an additional GIN-plan eligibility test (255 distinct backend tests). Ruff, strict mypy, fresh/restored migrations and model comparison passed; schema remains 20261114_0017.
- Frontend passed 68 tests, formatting, lint, typecheck and build. A restored real-data clone returned the stored Homo sapiens record for Homo sapines while normal search remained unchanged. Original table counts and previous application reads were preserved.

- Deployed HTTPS checks verified real name hints, identifier/scope/limit rejection, unchanged regular search and prior graph/catalogue/import status. Checked table counts/schema stayed unchanged and deployed CSS matched the retained frontend.

## [0.21.0] - 2026-11-14

### Added

- Durable GEO dataset metadata jobs through the existing protected batch API/CLI and singleton worker, with idempotence, bounded retries and terminal source-conflict handling.
- A public read-only import activity endpoint/page with grouped job/item counts and queue timestamps. Worker availability remains explicitly unknown; direct CLI imports are outside queue history. Private identifiers/results/errors are not exposed.
- Migration 20261114_0017 widens the queue type constraint without deleting data; downgrade refuses to discard dataset job compatibility. Old workers must not process dataset jobs.

### Changed

- Retained the new flat high-contrast research frontend and reused shared tables and states for import activity.

### Verified

- 240 backend tests on isolated PostgreSQL, Ruff, strict mypy, fresh/restored migrations and Alembic model comparison passed. Frontend passed 65 tests, formatting, lint, typecheck and production build.
- A real GSE10072 metadata refresh completed through the queue on the restored clone with original biological counts preserved. Aggregate counts matched and downgrade was correctly refused while dataset history existed. The previous application read biological catalogues on the widened schema.

- Deployed HTTPS verified aggregate privacy, protected job details, existing reads and blocked writes. Original table counts stayed unchanged; no live jobs were enqueued. Deployed CSS matches the retained research frontend.

## [0.20.0] - 2026-11-13

### Added

- Local JSON/GraphML downloads of the visible explored graph, preserving typed identities, complete source assertions, direction and partial-view context.
- Explicit scope, browser export timestamp, application version and initial request metadata; source dates remain distinct and collapse omits hidden branches.
- Accessible failure reporting, expansion-aware controls, escaped namespaced XML and JSON fallback for unsupported XML text. No database schema changes or additional dependencies.

### Verified

- 230 backend tests on isolated PostgreSQL, fresh/restored migrations, Alembic comparison, Ruff and strict mypy passed; schema head remains 20261112_0016.
- Frontend passed 62 tests, formatting, lint, typecheck and production build, including evidence/XML round trips, collapsed scope, partial status, download lifecycle and accessible errors.
- Restored backup counts matched live data and retained 0.19 rollback images passed smoke checks.

- The real public dataset citation graph exported to JSON/GraphML and passed an independent XML parse with source evidence preserved. Deployed frontend/chunk assets, API/graph behavior and blocked writes passed HTTPS checks; checked database totals stayed identical.

## [0.19.0] - 2026-11-12

### Added

- Typed first observed GEO dataset publication citations with exact local PMID resolution, source dates, provenance and idempotent protected API/CLI operations. Missing citations are reported without fetching or fabricating records.
- Dataset nodes and citation edges in bounded graph traversal and filters; bidirectional relationship reads, detail navigation and source inspection. Current metadata and retained first observed references are explicitly distinguished.
- Additive migration 20261112_0016 with restrictive foreign keys and unique pair identity. Downgrade refuses to discard assertions.

### Verified

- 230 backend tests on isolated PostgreSQL, Ruff, strict mypy, fresh/restored migrations and Alembic model comparison passed. Frontend passed 55 tests, formatting, lint, typecheck and production build.
- Restored live data accepted the real source-reported PMID 18297132 and one dataset citation, without additional gene links. Repeated resolution created no duplicate.

- Deployed HTTPS checks verified both citation directions, graph bounds/filters, provenance, SPA assets and blocked writes. Original data remain; one real PubMed citation and one sourced dataset edge were added.

## [0.18.0] - 2026-11-12

### Added

- Repository-scoped dataset metadata, a bounded public GEO Series self-record adapter and explicit idempotent CLI import with source-date regression protection.
- Dataset catalogue/detail, source access/publication references and a thirteenth unified search category. No raw files, tissue/disease inference or automatic local citation linking.
- Protected administrator creation and bounded reads; additive migration 20261112_0015 preserves prior data. Source contact fields are not stored.

### Verified

- 221 backend tests on isolated PostgreSQL, fresh and restored migrations, Alembic comparison, Ruff and strict mypy passed. Frontend passed 54 tests, formatting, lint, typecheck and production build.
- Restored pre-release data survived the additive migration; the previous 0.17 backend read the upgraded schema successfully. A bounded GSE10072 metadata import was verified on the restored copy.

- Public HTTPS verified the deployed catalogue/detail, GSE10072 metadata (107 sample records), search/suggestions, input bounds and blocked writes; all original entity totals remain unchanged.

## [0.17.0] - 2026-11-12

### Added

- PubMed-supplied keywords, bounded normalization/refresh, decoded Unicode keyword matching and keyword links on publication detail.
- Sourced publication–variant references through protected administrator writes, bidirectional relationships and graph traversal; mentions do not infer clinical significance.
- Additive migration 20261112_0014 retains prior data. No variant links or topics are inferred from article text.

### Verified

- 208 backend tests on isolated PostgreSQL, fresh/restored migrations, Alembic model comparison, Ruff and strict mypy passed; frontend passed 52 tests, formatting, lint, typecheck and build.
- A restored live backup successfully imported two real PubMed citations with five keywords each and zero inferred local gene links. Existing biological counts remained intact; retained 0.16 backend reads on the upgraded clone passed.

- Citation link creation serializes with variant identity updates; existing source placements or citations protect variant identity. The full PostgreSQL suite was rerun after this safeguard.
- Deployed 0.17 with migration 20261112_0014; two real PubMed citations with five keywords each are public. HTTPS keyword/search/graph checks, original biological totals, SPA asset and blocked writes passed.

## [0.16.0] - 2026-11-12

### Added

- GO cellular-component terms, direct sourced protein annotations, same-aspect `is_a` hierarchy and restrictive composite keys via migration 20261112_0013.
- Cellular-component catalogue/detail, relationship and graph projections/filters, plus a twelfth unified search category.
- Existing GO contracts, cycle checks, source/evidence display and protected writes remain in use. No automatic ontology import, annotation propagation or enrichment is added; new collections start empty.

### Verified

- 202 backend tests on isolated PostgreSQL, fresh/restored migrations, Alembic model comparison, Ruff and strict mypy passed. Frontend passed 50 tests, formatting, lint, typecheck and build.
- Original biological/ontology counts were preserved after upgrading a restored live backup. The previous 0.15 backend successfully read that clone for application rollback.

- Deployed 0.16 via existing VPS/Compose; migration 20261112_0013, public CC/search/relationship/graph checks, original catalogue totals, SPA asset and blocked writes passed.

## [0.15.0] - 2026-11-11

### Added

- Source-backed literal variant placements with explicit assembly, versioned sequence, forward-strand one-based closed coordinates, bounded REF/ALT alleles and provenance.
- Protected administrator creation, paginated public reads and a genomic placement panel on variant detail. Duplicate source observations are constrained without indexing large allele strings.
- Parent variant identity/organism and organism-taxonomy guards once placements exist; additive migration 20261111_0012 preserves prior data.
- No automatic variant import, reference verification, liftover, normalization or clinical inference is added; the placement collection starts empty.

### Verified

- 195 backend tests on isolated PostgreSQL, fresh and restored migrations, Alembic model comparison, Ruff and strict mypy passed. Frontend passed 48 tests, formatting, lint, typecheck and build.
- Restored data counts remained unchanged after upgrade, the new placement table was empty and TP53 search still returned 42 results. The previous 0.14 backend successfully read the upgraded clone for application rollback.

- Deployed 0.15 via existing VPS/Compose; migration head 20261111_0012, public route/validation/search/quality checks, original catalogue totals, SPA asset and blocked writes passed.

## [0.14.0] - 2026-11-11

### Added

- Sourced HPO-identified phenotype terms and explicitly qualified disease annotations, additive migration 20261111_0011, restrictive foreign keys and duplicate assertion constraints.
- Protected administrator writes and paginated public reads in both directions, phenotype catalogue/detail and a phenotype panel on disease pages.
- Unified search/suggestions now include an eleventh `phenotype` category. Present/excluded source assertions remain distinct, with references, evidence and releases shown.
- New collections start empty; no real or synthetic phenotype import, automatic inference or scheduled synchronization is performed.

### Verified

- 174 backend tests on isolated PostgreSQL, fresh migrations, upgraded live backup, Alembic model comparison, Ruff and strict mypy passed.
- 46 frontend tests plus formatting, lint, typecheck and production build passed. Original starter data and TP53 search results were retained on the upgraded clone; new phenotype collections remained empty.

- Deployed 0.14 with migration 20261111_0011 through existing VPS/Compose; public phenotype/search/validation checks, original catalogue totals, SPA asset and blocked writes passed.

## [0.13.0] - 2026-11-11

### Added

- Unified search now includes transcripts, diseases, variants, pathways, GO biological processes and molecular functions alongside the existing four categories.
- Matching source context, counts, filters, suggestions and detail links across the expanded catalogue; exact stored transcript versions and HGVS-only variants are supported.
- Bounded search/suggestion execution with safe timeout errors. No schema migration or biological data import is required.

### Verified

- 161 backend tests on isolated PostgreSQL, migration/model comparison, Ruff and strict mypy passed; frontend passed 43 tests, formatting, lint, typecheck and production build.
- A restored live database retained 3 genes, 3 proteins, 128 transcripts and six evidenced gene identities. Searching TP53 returned the gene, its protein and 40 stored transcripts, with 42 total results.

- Deployed 0.13 via existing VPS/Compose; public HTTPS search/filter/version/suggestion checks, original catalogue totals, SPA asset and blocked writes passed.

## [0.12.0] - 2026-11-11

### Added

- Read-only `/api/v1/data-quality` and `/data-quality` page with ten scoped metadata, identifier consistency, organism consistency and refresh review checks.
- Bounded record examples, organism-specific gene links, explicit fixture exclusion and safe review timeouts. Coverage and retrieval age are distinguished from scientific correctness.
- No schema migration, biological imports, data corrections or automatic refresh in this release. Existing APIs remain compatible.

### Verified

- 151 backend tests on isolated PostgreSQL, migration/model comparison, Ruff and strict mypy; 41 frontend tests, formatting, lint, typecheck and production build passed.
- A fresh live-data backup was restored with 3 genes, 3 proteins, 128 transcripts and 6 evidenced identities preserved. The new review completed on that clone without findings in its ten scoped checks.

- Deployed 0.12 through the existing VPS/Compose setup; public HTTPS report, interval validation, SPA asset, original catalogue counts and blocked writes passed.

## [0.11.0] - 2026-11-11

### Added

- Namespaced NCBI/Ensembl gene identity registry, bounded source evidence, exact observed-version resolution and provenance display on gene detail. Additive migration 20261111_0010.
- UniProt explicit cross-reference ingestion enables Ensembl mapping without symbol guessing or gene merging; conflicts roll back the record.

### Fixed

- Ensembl species metadata accepts strict decimal taxonomy strings; JSON requests use the validated documentation-style query.
- Unknown explicit NCBI identifiers no longer fall back to gene symbols. Worker retry tests derive their clock from queued work.

### Verified

- 142 backend tests on isolated PostgreSQL, migration/model comparison, Ruff and strict mypy passed. Frontend validation passed 38 tests, formatting, lint, typecheck and build.
- Live bounded imports added 128 Ensembl transcripts (TP53 40, BRCA1 59, PINK1 29) using explicit UniProt mappings; public HTTPS/API checks passed. Scheduled refresh remains disabled.
- Pre-release backup was restored and upgraded with original record counts preserved; previous application images were retained and smoke-tested.

## [0.10.0] - 2026-11-07

### Added

- First-class sourced transcripts, explicit Ensembl parent/species/assembly validation, atomic idempotent CLI imports and additive migration 20261107_0009.
- Transcript browser/detail, scoped filtering and observed transcripts on gene detail; gene identifier/organism safeguards protect source parent identity.
- Actual initial NCBI gene and UniProt protein records loaded through existing source adapters after the user's request for data. Private contact configuration is excluded from Git.

### Verified

- 117 backend and 36 frontend tests, fresh PostgreSQL migrations/model comparison and lint/typing/build checks passed. Live Ensembl metadata returned provider errors; no successful real transcript import is claimed.
- Public API confirmed three genes, three proteins, source provenance and the TP53 protein link. Periodic synchronization remains disabled.

## [0.9.0] - 2026-11-07

### Added

- Source-backed gene aliases and reference sequence placements, including normalized NCBI source fields, all bounded placements and per-observation provenance.
- Alias-aware unified search with canonical identity, deduplicated counts and exact-symbol precedence; source context on the gene detail page.
- Additive migration 20261107_0008, taxonomy/organism safeguards and a coverage map of the owner's long-term roadmap.

### Compatibility

- Preserved existing gene list/ID responses, legacy coordinate columns and import/job contracts. No inferred assemblies, automatic data backfill or real imports.

## [0.8.0] - 2026-11-07

### Added

- Durable, bounded NCBI Gene / UniProt / PubMed import jobs, protected administrator API, host CLI and an optional PostgreSQL queue worker.
- Per-record progress/results, request idempotency, cancellation, capped transient retries, shared HTTP pacing and crash recovery using existing provenance-preserving ingestion.
- Additive migration 20261107_0007 and tests for PostgreSQL worker exclusion, crash replay, cancellation, authorization and all provider dispatch paths.

### Changed

- Updated application version and frontend phase/About text to Phase 8. The public API proxy remains read-only and workers/imports are opt-in.
- Documented Phase 8 operations, at-least-once recovery and the existing temporary public-preview deployment path.

## [0.4.0] - 2026-09-21

### Added

- `Disease` and `Variant` models, validation schemas, repositories, services, paginated CRUD/read APIs, and identifier lookup routes.
- Four typed association tables for gene–disease, variant–gene, variant–disease, and protein–protein assertions, each with source identifiers, optional evidence/source URLs, timestamps, foreign keys, and source-scoped deduplication.
- Paginated relationship API with typed nodes and predicates; existing gene→protein links are projected with clearly identified protein-record provenance.
- Disease and variant list/detail pages and a reusable relationship panel on all four connected entity pages.
- Phase 4 backend and frontend tests for provenance, links, pagination, validation, duplicates, and empty states.
- Additive migrations `20260921_0003` and `20260921_0004` for the new schema and self-protein interactions.

### Changed

- Canonicalized undirected protein interaction pairs while allowing self- and cross-organism interactions.
- Prevented gene/variant organism changes that would invalidate existing organism-scoped links.
- Aligned ORM unique-constraint metadata with the already applied schema; documented and isolated PostgreSQL full-text expression indexes from unreliable Alembic expression comparisons.
- Updated API, package, frontend, and provider user-agent versions to `0.4.0`.

### Verified

- Twenty-four backend tests and eleven frontend tests pass, with lint, formatting, typing, and frontend production build checks.
- Both Phase 4 migrations applied to PostgreSQL 17; Alembic reports head with no pending schema operations. Live API/frontend smoke checks preserve search and expose existing encoding links.

### Known limitations

- Disease/variant records and associations require source-backed API entry; no automated MONDO/ClinVar/dbSNP ingestion or fictional default data was added.
- The write API has no authentication, relationship evidence is not a scientific confidence score, and organism-scoped cross-table integrity relies partly on service validation.
- Fresh Docker build, fresh-database migration replay, and large-corpus relationship benchmarks remain unverified from this shell.

## [0.3.0] - 2026-09-21

### Added

- Unified `SearchService` across genes, proteins, and organisms with exact-identifier weighting, partial and multi-term matching, deterministic ranking, category counts, filters, pagination, matched-field excerpts, and bounded suggestions.
- Typed `GET /api/v1/search` and `GET /api/v1/search/suggestions` contracts, plus an unadvertised `/api/search` compatibility alias.
- Alembic migration `20260920_0002` enabling `pg_trgm` and adding trigram and full-text GIN search indexes.
- Search results page with shareable query/filter/page URLs, category counts, provenance-aware cards, safe match highlighting, suggestions, and loading/empty/retryable-error states.
- Backend search tests and frontend search interaction tests, including PostgreSQL query-expression compilation coverage.

### Changed

- Gene search links now carry organism taxonomy context; gene detail lookup reads it while preserving the previous human default for bare links.
- API and package metadata identify version `0.3.0`; documentation describes the implemented Phase 3 behavior and Phase 4 boundary.

### Verified

- Twenty-one backend and eight frontend tests pass with lint, formatting, type checks, and a production frontend build.
- Live API/frontend smoke checks pass; read-only PostgreSQL 17 checks confirm the Phase 3 revision, twelve search indexes, and ranked symbol, accession, identifier, organism, and multi-term queries.

### Known limitations

- Search is local to stored genes, proteins, and organisms; it has no alias/synonym or fuzzy typo support yet.
- Rank quality and query plans need testing on a representative large corpus. A fresh Docker build and migration were not run from this implementation shell.
- Organism records appear in results but do not yet have a detail page.

## [0.2.0] - 2026-09-20

### Added

- Shared synchronous JSON transport with configurable timeout, bounded exponential retries, numeric `Retry-After` handling, structured retry logging, and safe upstream error types.
- NCBI Gene adapter using exact symbol/taxonomy ESearch and ESummary requests with required tool-owner identification and optional API key support.
- UniProtKB adapter for accession-based protein retrieval.
- Provider-independent Pydantic normalization models for organisms, genes, proteins, and source provenance.
- Explicit zero-based to one-based inclusive NCBI coordinate normalization with strand preservation.
- Idempotent `GeneIngestionService` and `ProteinIngestionService` workflows with stable-ID matching, organism upsert, transaction rollback, and safe gene–protein linkage.
- `import-gene` and `import-protein` CLI commands with JSON results and machine-readable failure output.
- Explicit gene-symbol/taxonomy and protein-accession read APIs.
- Gene and protein detail pages with biological fields, identifiers, local relationships, retrieval metadata, and canonical provider links.
- Mocked adapter tests, retry tests, normalization tests, idempotent ingestion tests, relationship lookup tests, and frontend detail-page tests.

### Changed

- Promoted `httpx2` from a test-only dependency to a backend runtime dependency.
- Updated entity list tables to link to stable detail routes.
- Extended Compose environment forwarding for provider configuration without adding services.
- Updated API metadata to version `0.2.0`.
- Updated `README.md` and `ARCHITECTURE.md` with Phase 2 operation, data flow, verification evidence, limitations, and the Phase 3 plan.

### Preserved

- Existing Phase 1 endpoints, database schema, migration history, demo fixture loader, and three-service development topology.
- Network-independent automated tests; live providers are not required by the test suite.

### Known limitations

- Provenance remains record-level and does not retain claim history, provider releases, raw payloads, checksums, or import-job history.
- NCBI assembly/accession and alternate genomic placements are not persisted.
- Imports are bounded single-record synchronous CLI operations; bulk/background ingestion is deferred.
- Docker/PostgreSQL execution remains unverified on this host because Docker and a local PostgreSQL service are unavailable.
- Live NCBI verification requires a project-owner contact email; no false contact identity was used during implementation.
- Unified ranked search remains Phase 3 work.

## [0.1.0] - 2026-09-20

### Added

- Phase 0 repository assessment documenting that the repository began without application files or commit history.
- Project overview, product principles, initial domain scope, API conventions, planned repository layout, and Phase 1 summary in `README.md`.
- Modular-monolith architecture covering the React frontend, FastAPI layers, PostgreSQL persistence, future integration/normalization flow, and operational boundaries.
- Initial `Organism`, `Gene`, and `Protein` conceptual schemas and relationship rules.
- Record-level provenance baseline and an evolution path for import and evidence provenance.
- API naming, pagination, error, configuration, logging, database migration, and testing conventions.
- FastAPI application factory with environment configuration, structured/human-readable logging modes, request IDs, CORS, liveness health check, OpenAPI, and normalized error responses.
- Typed SQLAlchemy models, repositories, application services, Pydantic schemas, validation constraints, indexes, and PostgreSQL relationships for organisms, genes, and proteins.
- Versioned paginated list/detail/create/update endpoints for all three initial entities.
- Initial Alembic migration with deterministic constraints, indexes, restrictive foreign keys, and downgrade support.
- Idempotent CLI fixture loader and explicitly marked development-only organism, gene, and protein fixtures.
- React, TypeScript, and Vite frontend with Home, Search, Genes, Proteins, About, and not-found routes.
- Reusable navigation, search, entity card, responsive data table, pagination, provenance, loading, empty, and error components.
- Responsive scientific visual design with accessibility labels, visible demo-data notices, and reduced-motion behavior.
- Dockerfiles and Docker Compose configuration for PostgreSQL, FastAPI, and Vite development services.
- Backend tests for health/OpenAPI, CRUD, pagination, validation, conflicts, relationship integrity, and fixture idempotency.
- Frontend tests for API-backed entity display, provenance, retry behavior, and non-fabricated search messaging.
- Ruff, mypy, pytest, ESLint, Prettier, TypeScript, Vitest, and Vite build configuration.

### Changed

- Updated `README.md` from the Phase 0 proposal to runnable development, API, fixture, verification, and limitation documentation.
- Updated `ARCHITECTURE.md` to distinguish implemented Phase 1 behavior from the Phase 2 plan and to record verification evidence.

### Known limitations

- Live NCBI/UniProt ingestion and ranked unified search are not implemented.
- Write endpoints are unauthenticated and intended for controlled development only.
- Docker Compose and a live PostgreSQL migration could not be executed on the implementation host because Docker/PostgreSQL were unavailable; Compose structure and PostgreSQL migration SQL generation passed.
- PostgreSQL-specific application integration remains to be added to CI; isolated tests currently use SQLite.
- Provenance is record-level pending real multi-source ingestion behavior.
- No open-source license has been selected yet.
