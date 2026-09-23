# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project intends to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once versioned application releases begin.

## [Unreleased]

### Fixed

- Made frontend Compose startup populate or repair its Linux `node_modules` volume from the committed pnpm lockfile before launching Vite.
- Excluded host `node_modules`, virtual environments, caches, build output, logs, and local environment secrets from Docker build contexts, preventing Windows dependency artifacts from overwriting container-installed packages.

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
