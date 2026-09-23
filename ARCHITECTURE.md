# Architecture

## 1. Purpose and status

This document describes the architecture implemented through Phase 4 of the Bioinformatics Knowledge Platform and identifies the boundaries reserved for later phases.

The repository was empty when Phase 0 began. Phase 1 established the runnable modular monolith; Phase 2 added bounded, synchronous NCBI Gene and UniProtKB ingestion; Phase 3 added unified PostgreSQL search; Phase 4 added disease/variant entities and sourced relational assertions without a graph database or background worker.

## 2. Architectural goals

The architecture should support:

- reliable exploration of linked biological entities;
- traceability of imported records and relationships;
- progressive addition of providers and entity types;
- useful API and UI behavior on large, paginated datasets;
- independently testable domain, persistence, API, and integration logic;
- local development through a small, reproducible container stack; and
- evolution from simple relational lookup to full-text search and graph traversal without replacing PostgreSQL as the source of truth.

The architecture does not currently optimize for independently deployed services, bulk or scheduled ingestion, a separate graph database, or a dedicated search cluster. Those remain future options rather than Phase 4 dependencies.

## 3. System context

```text
                                  read/query
Researcher  -->  Web browser  ----------------->  HTTP API
                     |                              |
                     | React application            | FastAPI
                     v                              v
                rendered UI                  application services
                                                    |
                                                    v
                                              repositories
                                                    |
                                                    v
                                                PostgreSQL

Public scientific APIs  -->  adapters  -->  normalization  -->  ingestion services
                                                                    |
                                                                    v
                                                                PostgreSQL
```

The browser never communicates directly with PostgreSQL or external biological providers. External API behavior is isolated from both the REST interface and internal persistence models.

## 4. Architecture style

The initial system is a **modular monolith** with a separate single-page frontend:

- one FastAPI backend process;
- one React application built with Vite;
- one PostgreSQL database; and
- one Docker Compose project for development.

Internally, backend dependencies point inward:

```text
API routes -> services -> repositories -> SQLAlchemy/database
                    ^
                    |
          normalized internal inputs
                    ^
                    |
       external provider adapters
```

Routes are responsible for HTTP translation, not business rules. Services coordinate use cases and transaction boundaries. Repositories encapsulate query and persistence details. SQLAlchemy models describe storage; Pydantic schemas describe inputs and outputs. Provider adapters map external payloads into typed normalized objects before ingestion services see them.

This structure makes later extraction of a job worker or search index possible, while avoiding premature distributed-system complexity.

## 5. Component responsibilities

### 5.1 Frontend

The React/TypeScript frontend owns:

- routing and shareable URLs;
- accessible, responsive presentation;
- query parameter and pagination state;
- reusable navigation, search, entity card, table, loading, empty, and error components;
- typed calls to the backend; and
- clear display of demo-data and provenance labels.

It does not encode provider-specific response structures or scientific facts. A small API client boundary converts transport failures into UI states. Phase 2 added gene/protein detail layouts; Phase 3 added URL-backed ranked search; Phase 4 added disease/variant list and detail views plus a reusable relationship panel with evidence and source context. Server-state caching can be added when concrete usage justifies it; the current read flows do not require a large global state library.

### 5.2 API layer

FastAPI routers own:

- URL and method definitions;
- request parsing and Pydantic validation;
- dependency injection for database sessions and services;
- translation of domain/application errors into the standard error envelope; and
- response schemas and OpenAPI documentation.

Routers must not contain raw SQL, provider calls, or multi-step ingestion logic.

### 5.3 Service layer

Services represent application use cases. They own:

- coordination across repositories;
- application-level validation not expressible in schemas;
- transaction decisions for a use case;
- duplicate and conflict semantics; and
- future ingestion and search orchestration.

Simple reads may be thin, but maintaining this seam avoids coupling HTTP endpoints directly to persistence.

### 5.4 Repository layer

Repositories own:

- SQLAlchemy query construction;
- filtering, ordering, pagination, and eager-loading decisions;
- entity lookup by internal and external identifiers; and
- persistence operations requested by services.

Repositories return internal ORM/domain objects, not FastAPI responses. Collection queries must filter and paginate in the database; they must not load an entire table into application memory.

### 5.5 Persistence

PostgreSQL is the system of record. SQLAlchemy 2.x provides explicit typed mappings and session management. Alembic is the only supported mechanism for evolving shared schema history.

The backend uses synchronous SQLAlchemy. The synchronous stack is simpler to reason about, test, and operate; FastAPI runs the regular route functions in its thread pool. This decision can be revisited without changing API contracts or service boundaries if profiling shows database concurrency is a bottleneck.

### 5.6 Integrations and ingestion

Phase 2 implements this flow:

```text
HTTP client -> provider adapter -> normalized typed record -> ingestion service -> repository
```

- **Shared HTTP client:** JSON response validation, configurable timeout, bounded exponential backoff, numeric `Retry-After` support, logging, and safe typed failures. Only timeouts, transport failures, `429`, and `5xx` responses retry.
- **NCBI Gene adapter:** exact symbol plus taxonomy lookup through ESearch followed by ESummary. Requests carry the configured tool and required contact email; an API key is optional. Provider zero-based coordinates are normalized to one-based inclusive start/end values and transcription direction is preserved as strand.
- **UniProt adapter:** direct UniProtKB accession retrieval. The adapter extracts canonical accession, recommended/submitted protein name, organism, first gene symbol, GeneID cross-reference, function comments, and sequence length.
- **Normalized record:** provider-independent typed representation with explicit optionality and validation.
- **Ingestion service:** stable-ID matching, organism upsert, create/update/unchanged decisions, safe gene linkage, provenance refresh, rollback, and one transaction per record.
- **Repository:** database lookup and writes.

Imports are explicit CLI operations, not long-running HTTP requests. Raw provider payloads do not cross into API response schemas or become the domain model.

## 6. Implemented repository structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   └── v1/
│   │       ├── diseases.py
│   │       ├── genes.py
│   │       ├── organisms.py
│   │       ├── proteins.py
│   │       ├── relationships.py
│   │       ├── search.py
│   │       ├── variants.py
│   │       └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── logging.py
│   ├── models/
│   ├── ingestion/
│   │   ├── models.py
│   │   └── services.py
│   ├── integrations/
│   │   ├── ncbi/
│   │   ├── uniprot/
│   │   ├── errors.py
│   │   └── http.py
│   ├── repositories/
│   ├── search/
│   ├── schemas/
│   ├── services/
│   ├── cli.py
│   ├── fixtures.py
│   └── main.py
├── migrations/
├── tests/
└── pyproject.toml

frontend/
├── src/
│   ├── components/
│   ├── hooks/
│   ├── pages/
│   ├── services/
│   ├── test/
│   └── types/
└── package.json
```

The `search/` package owns the Phase 3 cross-entity query. Its SQLAlchemy query construction stays in a focused service because it spans three entities and is specific to relevance ranking. `services/relationships.py` similarly owns the Phase 4 cross-table incident-edge query; CRUD repositories remain responsible for entity operations. Empty layers and speculative interfaces are not generated merely to match a diagram.

## 7. Initial data model

All primary keys are database-generated `BIGINT` values. Timestamps are timezone-aware UTC values. Mutable records contain `created_at` and `updated_at`; imported records also carry import/source metadata. Scientific identifiers are stored as strings even when they appear numeric because formatting and provider semantics matter.

### 7.1 Organism

| Field | Type | Constraints/notes |
| --- | --- | --- |
| `id` | bigint | primary key |
| `scientific_name` | text | required |
| `common_name` | text | nullable |
| `taxonomy_id` | text | nullable, unique when present; NCBI taxonomy identifier |
| `source` | text | required; `development_fixture` for Phase 1 fixtures |
| `source_identifier` | text | nullable |
| `source_url` | text | nullable |
| `imported_at` | timestamptz | nullable for manually authored records |
| `created_at` | timestamptz | required |
| `updated_at` | timestamptz | required |

### 7.2 Gene

| Field | Type | Constraints/notes |
| --- | --- | --- |
| `id` | bigint | primary key |
| `symbol` | text | required; indexed with `organism_id` |
| `name` | text | required |
| `description` | text | nullable |
| `organism_id` | bigint | required foreign key to `organisms.id` |
| `chromosome` | text | nullable; not assumed to be numeric |
| `start_position` | bigint | nullable; non-negative when present |
| `end_position` | bigint | nullable; not less than `start_position` when both exist |
| `strand` | text | nullable; constrained to `+` or `-` initially |
| `ncbi_gene_id` | text | nullable, unique when present |
| `ensembl_gene_id` | text | nullable, unique when present |
| `source` | text | required |
| `source_identifier` | text | nullable |
| `source_url` | text | nullable |
| `imported_at` | timestamptz | nullable |
| `created_at` | timestamptz | required |
| `updated_at` | timestamptz | required |

Gene symbols are not globally unique. Phase 1 may enforce uniqueness for `(organism_id, symbol)` for its controlled fixture set, but ingestion must later account for synonyms, retired symbols, and provider-specific conflicts rather than treating a symbol as a universal identifier.

### 7.3 Protein

| Field | Type | Constraints/notes |
| --- | --- | --- |
| `id` | bigint | primary key |
| `accession` | text | required, unique, indexed |
| `name` | text | required |
| `gene_id` | bigint | nullable foreign key to `genes.id` |
| `organism_id` | bigint | required foreign key to `organisms.id` |
| `function` | text | nullable |
| `sequence_length` | integer | nullable, positive when present |
| `source` | text | required |
| `source_identifier` | text | nullable |
| `source_url` | text | nullable |
| `imported_at` | timestamptz | nullable |
| `created_at` | timestamptz | required |
| `updated_at` | timestamptz | required |

The initial `gene_id` models a simple encoding link and is nullable because not every protein record can be resolved immediately. If real sources require multiple gene associations, the field will migrate to an explicit association table rather than embedding arrays or comma-separated identifiers.

### 7.4 Initial relationships

```text
Organism 1 ---- * Gene
Organism 1 ---- * Protein
Gene     1 ---- * Protein  (optional from the Protein side)
```

Delete behavior should be restrictive for scientific entities. Entity deletion is not the primary correction strategy; updates, deprecation status, and source-history decisions will be introduced when real ingestion semantics are known.

## 8. Relationship evolution

The long-term graph will be represented relationally first. The design favors **typed association tables** where they provide referential integrity and domain-specific metadata, for example:

- `gene_disease_associations`;
- `variant_gene_locations`;
- `variant_disease_associations`;
- `protein_interactions`; and
- `gene_pathway_memberships`.

Each association can carry a controlled predicate, provenance reference, evidence summary or evidence identifier, curation/extraction method, confidence where the source supplies a meaningful value, and timestamps.

A single unrestricted entity-attribute-value table would make foreign keys, validation, query planning, and domain constraints unnecessarily weak. A lightweight unified read projection may later expose typed tables through graph traversal endpoints. Neo4j is optional only if measured traversal needs cannot be served acceptably by PostgreSQL.

## 9. Provenance strategy

Provenance is additive and must survive normalization.

### Implemented through Phase 2: record-level provenance

Each seed entity stores:

- `source` — stable provider key or `development_fixture`;
- `source_identifier` — identifier as represented by the source;
- `source_url` — canonical human-usable record URL when available;
- `imported_at` — time retrieved/loaded; and
- `created_at` / `updated_at` — local persistence history.

Real NCBI Gene and UniProtKB imports populate these fields with a provider name, stable identifier, canonical human-facing record URL, and UTC retrieval time. Re-importing refreshes `imported_at`. Existing fixture records are replaced with provider-backed values only when stable matching identifies the same canonical entity. Fixture files and UI surfaces continue to label all remaining demo data.

### Deferred provenance history

Phase 2 deliberately retains the existing record-level columns because each implemented canonical entity currently has one authoritative import provider: NCBI Gene for genes and UniProtKB for proteins. It does not add empty import-job or claim tables before batch ingestion and multi-source field merging exist.

When multiple providers contribute competing values to one entity, provenance must move to typed source/claim records rather than overwrite the canonical record. Future import history should capture provider release/version when available, canonical/request URL, payload checksum, parser version, and import job. Complete raw payload retention must be bounded and deliberate rather than an unbounded JSON column by default.

## 10. API conventions

### 10.1 Resource naming and versioning

- `GET /api/health` is an unversioned liveness endpoint for operations.
- Domain routes begin with `/api/v1`.
- Resource paths are plural lowercase nouns: `/api/v1/genes`, `/api/v1/proteins`, `/api/v1/organisms`.
- Internal numeric detail routes remain available: `/api/v1/genes/{gene_id}`.
- Explicit scientific-identifier routes avoid guessing identifier types: `/api/v1/genes/by-symbol/{symbol}?taxonomy_id=9606` and `/api/v1/proteins/by-accession/{accession}`.
- Search uses `/api/v1/search?q=...`; repeated `type` parameters narrow the returned page while per-category counts remain global. `/api/search` is an undocumented compatibility alias.
- JSON uses `snake_case`.

Breaking contract changes require a new API version. Additive fields may be introduced within `v1` when clients can safely ignore them.

### 10.2 Collections and pagination

Collection and search endpoints accept:

- `page`: one-based positive integer, default `1`;
- `page_size`: positive integer with a conservative default and maximum; and
- stable resource-appropriate filters only when implemented and indexed.

The response shape is:

```json
{
  "items": [],
  "page": 1,
  "page_size": 25,
  "total": 0,
  "pages": 0
}
```

CRUD collections use a deterministic secondary sort by primary key. Search orders by descending score, case-folded primary label, entity type, and internal ID. Offset pagination remains the current strategy. Cursor pagination can be added for high-volume traversal if benchmarking shows it is needed.

### 10.3 Mutation semantics

Phase 1 exposes controlled-development create/update endpoints with these semantics:

- `POST` returns `201 Created` and a resource representation;
- `PATCH` performs partial updates and returns the updated resource;
- attempts to create a conflicting stable identifier return `409 Conflict`; and
- validation failures return `422 Unprocessable Entity`.

Hard-delete endpoints should not be introduced until lifecycle and provenance-retention policy is defined.

### 10.4 Error envelope

Expected errors use a stable shape:

```json
{
  "error": {
    "code": "gene_not_found",
    "message": "Gene 123 was not found.",
    "details": null,
    "request_id": "optional-correlation-id"
  }
}
```

Rules:

- `code` is stable and machine-readable;
- `message` is safe for users and contains no stack trace, SQL, secret, or upstream payload;
- `details` may contain structured validation context;
- unexpected exceptions are logged with correlation context and returned as a generic `500` response;
- CLI integration failures use safe machine-readable codes and a non-zero exit status; no fallback facts are fabricated; and
- API validation errors are normalized to the same top-level envelope.

## 11. Configuration, security, and logging

Configuration is loaded from the repository-root `.env` file and environment variables through Pydantic settings. Implemented settings include:

- application environment and log level;
- database URL;
- allowed CORS origins; and
- fixture-loading controls;
- external timeout, retry count/backoff, and user agent;
- NCBI base URL, tool name, required contact email, and optional secret API key; and
- UniProt base URL.

A committed `.env.example` contains only safe examples. Secrets are never embedded in frontend code, images, fixtures, or Git history.

Logs should be structured and emitted to stdout. Each HTTP request should have a request/correlation ID, method, path, status, and elapsed time. Sensitive query values and full biological provider payloads should not be logged by default. Development logs may be human-readable; production configuration should use JSON.

CORS is allow-list based. A wildcard must not be combined with credentials. Phase 1 has no authentication and must not imply that administrative mutation endpoints are production-ready.

## 12. Database migration strategy

Alembic migration files live under `backend/migrations/` and are committed with schema changes.

Rules:

1. The initial migration creates `organisms`, `genes`, `proteins`, constraints, and indexes. Migration `20260920_0002` adds PostgreSQL search indexes; `20260921_0003` adds Phase 4 entities and assertions; `20260921_0004` permits self-protein interactions. Applied migrations are not rewritten.
2. Each later schema change gets a new forward migration; applied migration history is not rewritten.
3. Autogenerated migrations are manually reviewed for types, nullability, names, indexes, foreign keys, and downgrade behavior.
4. Application startup does not silently run migrations. Docker development startup uses an explicit migration command/service before serving traffic.
5. Fixture loading is a separate idempotent command, never migration logic.
6. Production migrations must be backed up and tested on representative data before destructive changes.

Constraint and index names follow deterministic conventions configured on SQLAlchemy metadata. Phase 4 aligned the ORM's unique-constraint metadata with the applied migrations. The three manually reviewed PostgreSQL full-text expression indexes are declared in metadata but excluded by name from Alembic's autogenerate comparison because PostgreSQL deparses their expressions with casts/parentheses that Alembic cannot compare reliably; index existence and query expression order have separate checks. Other schema changes remain visible to `alembic check`.

## 13. Testing and quality strategy

### 13.1 Backend

- **Unit tests:** schema validation, service rules, pagination boundaries, and error mapping.
- **Repository/integration tests:** PostgreSQL-backed constraints and queries. SQLite alone is not an adequate substitute for PostgreSQL behavior.
- **API tests:** FastAPI test client with dependency overrides and an isolated test database.
- **Migration smoke test:** upgrade a fresh PostgreSQL database to head.
- **Fixture test:** load demo data twice and verify idempotency.

External integration tests use hand-authored mocked provider responses and an in-process mock HTTP transport. Automated tests never depend on live NCBI or UniProt availability. Optional live smoke checks are manual verification only.

Backend quality gates should include Ruff lint/format checks, pytest, and pragmatic mypy coverage beginning at service and schema boundaries.

### 13.2 Frontend

- Component tests cover reusable loading, error, empty, table, and entity-card states.
- Page tests cover successful and failed API states and navigation.
- API client tests cover response/error translation.
- ESLint, Prettier checks, TypeScript compilation, tests, and a production Vite build are required gates.

Browser end-to-end testing can be introduced once flows span multiple pages and justify its maintenance cost.

### 13.3 Test data

Test and development fixtures are small, deterministic, and explicitly labeled `development_fixture`. They must not be represented as current or authoritative biological facts. Tests should assert identifiers and relationships required by behavior, not large copied snapshots of third-party payloads.

## 14. Operational boundaries

Phase 4 Docker Compose still includes exactly three long-running services:

- `db` — PostgreSQL with a health check and named development volume;
- `backend` — FastAPI development server after the schema is migrated; and
- `frontend` — Vite development server configured to call the backend.

Redis, Celery/RQ, OpenSearch/Elasticsearch, Neo4j, object storage, and monitoring stacks are intentionally absent. They are introduced only in the roadmap phases that need them and only with documented operational ownership.

The health endpoint reports process liveness without exposing secrets. PostgreSQL has its own Compose health check. A database-aware application readiness endpoint is deferred to production hardening; when added, liveness and readiness semantics must remain distinct.

## 15. Key architecture decisions

| Decision | Choice | Rationale | Revisit when |
| --- | --- | --- | --- |
| Deployment shape | Modular FastAPI monolith plus React SPA | Clear boundaries without distributed-system overhead | Independent scaling or release cadence is measured |
| Source of truth | PostgreSQL | Strong relational integrity, mature indexing/search, suitable initial graph tables | Never displaced by a derived index without an explicit migration plan |
| ORM/migrations | SQLAlchemy 2.x and Alembic | Typed persistence and reviewable schema history | Only for a demonstrated blocker |
| Backend DB mode | Synchronous initially | Lower implementation and operational complexity | Profiling shows database concurrency is limiting throughput |
| Internal primary keys | `BIGINT` | Compact indexes and efficient joins at large scale | Stable public opaque IDs become a concrete requirement |
| Search | PostgreSQL full-text and trigram indexes, with explicit exact-match scoring | Keeps search next to the source of truth while enabling useful partial matching | Search quality or scale becomes a measured limitation |
| Relationship storage | Typed relational association tables | Foreign keys, deduplication, and indexed endpoint traversal without EAV | Traversal requirements exceed practical PostgreSQL limits |
| Provenance | Record-level for entities, assertion-level for new relationships | Makes each imported record/link traceable without speculative field-level claim tables | Multiple sources contribute competing field values or batch audit becomes required |
| Background jobs | None initially | Phase 1 operations are bounded | Phase 8 imports require retries, progress, or scheduling |

## 16. Phase 1 implementation record

### Repository and quality foundation

- Root environment example and ignore rules separate configuration, secrets, generated data, caches, builds, and dependencies from source.
- The backend package targets Python 3.12 and declares runtime and development dependency ranges in `pyproject.toml`.
- The frontend lockfile captures the resolved React/Vite toolchain.
- Ruff, mypy, pytest, ESLint, Prettier, TypeScript, Vitest, and the production Vite build are configured.
- An OSI-approved license remains unselected because that legal choice requires explicit project-owner direction.

### Backend and persistence

- `create_app()` assembles FastAPI, CORS, request IDs, logging, exception handlers, health routing, and the versioned API without connecting to the database at import time.
- Pydantic settings use `BKP_` environment variables and load the root `.env` file.
- SQLAlchemy models implement the three initial entities, referential constraints, validation constraints, indexes, record-level provenance, and timezone-aware timestamps.
- The reviewed `20260920_0001` migration creates and cleanly drops the Phase 1 schema.
- Focused repositories perform database pagination and relationship loading. Services own link validation, transaction boundaries, not-found behavior, and database conflict translation.
- The API provides paginated lists, details, creates, and partial updates. Hard deletion is omitted until a provenance-preserving lifecycle is designed.

### Fixtures and frontend

- `python -m app.cli load-fixtures` loads `development_demo` JSON only and is idempotent by stable fixture keys.
- Fixture identifiers are prefixed with `demo-` or `DEMO-`; descriptions and the UI state that they are non-authoritative.
- The React/Vite application implements Home, Search, Genes, Proteins, About, and not-found routes.
- Genes and Proteins fetch paginated API data through a typed client and expose loading, empty, retryable error, and success states.
- The Search page preserves `/search?q=...` URLs but explicitly refuses to synthesize results before Phase 3.
- CSS provides responsive navigation, scientific typography, entity cards, tables that become record cards on narrow screens, visible focus behavior, and reduced-motion handling.

### Development orchestration

- Docker Compose defines exactly `db`, `backend`, and `frontend` long-running services.
- PostgreSQL and backend health checks gate dependent startup.
- Backend startup explicitly runs Alembic and the idempotent fixture command before Uvicorn; migration logic is not hidden in application imports.
- Named volumes retain PostgreSQL and frontend dependency state.
- Frontend startup runs a frozen-lockfile install inside its Linux-only dependency volume before Vite starts. Docker build contexts exclude host dependencies, virtual environments, caches, builds, logs, and local secrets so Windows artifacts cannot overwrite container dependencies.

## 17. Phase 1 verification record

Verified on the implementation host:

- [x] Ruff formatting and lint checks pass.
- [x] Strict mypy analysis passes for the application package.
- [x] Nine backend tests pass across health/OpenAPI, pagination, CRUD, relationships, partial-update validation, error envelopes, conflicts, and fixture idempotency.
- [x] ESLint, Prettier, and TypeScript checks pass.
- [x] Three frontend tests pass for data, provenance, retry behavior, and honest search messaging.
- [x] The Vite production build succeeds.
- [x] Alembic generates valid PostgreSQL upgrade SQL through migration head.
- [x] The backend and frontend start locally for live smoke testing.
- [x] Health, OpenAPI, paginated genes, and paginated proteins return HTTP 200.
- [x] Loading fixtures twice creates `1/2/2` records on the first run and `0/0/0` on the second.
- [x] Browser-level responsive home and Genes pages render live API data with no console warnings or errors.
- [x] Compose YAML parses with the expected three services.

Not executable on this host:

- [ ] Run `docker compose up --build`; the Docker CLI is not installed.
- [ ] Apply the migration against a live PostgreSQL server; no local PostgreSQL service is available outside Docker.

The live smoke test used a disposable SQLite database created from SQLAlchemy metadata solely because Docker/PostgreSQL was unavailable. SQLite is not the configured application database and is not treated as proof of PostgreSQL runtime behavior.

## 18. Phase 1 limitations at completion (historical)

- NCBI and UniProt integrations, provider normalization, and retry behavior had not yet been implemented.
- The Search page is a transparent placeholder; ranked PostgreSQL search is Phase 3.
- Mutation endpoints have no authentication or authorization and are for controlled development use only.
- There is no hard-delete, deprecation, alias, or merge lifecycle for scientific entities.
- Provenance is record-level; claim-level conflicts and multiple provider contributions await real ingestion behavior.
- Genome assembly identifiers, transcripts, isoforms, gene aliases, taxonomy hierarchy, and sequence storage are deferred.
- The synchronous database stack and offset pagination have not been load-tested.
- The automated repository test suite uses SQLite for isolated persistence behavior; PostgreSQL migration/application integration needs a Docker-capable environment and later CI coverage.
- There is no CI, rate limiting, metrics, backup automation, production reverse proxy, or deployment configuration.
- The project has no selected open-source license.

## 19. Phase 2 implementation record

### Provider and normalization boundary

- `RetryingJsonClient` is the only provider transport policy. It validates JSON object responses, bounds retries, respects numeric `Retry-After`, caps waits, logs retry context without payloads, and translates provider failures into safe typed errors.
- `NcbiGeneAdapter` uses exact-symbol/taxonomy ESearch followed by ESummary. It requires a configured contact email, accepts an optional API key, and produces `NormalizedGene` plus `NormalizedOrganism` values.
- `UniProtAdapter` retrieves one UniProtKB accession and produces `NormalizedProtein` plus `NormalizedOrganism` values.
- Pydantic normalized models reject unknown fields and validate identifiers, names, taxonomy, coordinate bounds, strand, sequence length, URLs, and retrieval timestamps before persistence.
- Provider payload dictionaries are confined to adapter modules. Repositories, services, API schemas, ORM models, and frontend types do not depend on NCBI or UniProt response shapes.

### Idempotent persistence and CLI

- `GeneIngestionService` matches by NCBI GeneID, then by `(organism, symbol)`, rejects conflicting matches, and upserts one canonical gene in one transaction.
- `ProteinIngestionService` matches by UniProt accession and links to a local gene by GeneID first or organism-scoped symbol second. A missing gene leaves a nullable link; no partial scientific record is fabricated.
- Organisms match by taxonomy ID. A real provider may replace matching development-fixture provenance; one real provider does not overwrite another provider's organism provenance merely because both mention the same taxonomy.
- Imports report `created`, `updated`, or `unchanged`. Retrieval time is refreshed on every successful provider import even when scientific fields are unchanged.
- `python -m app.cli import-gene SYMBOL [--taxonomy-id TAXID]` and `import-protein ACCESSION` are bounded single-record commands with JSON output and non-zero safe JSON errors.

### Read API and frontend

- `GET /api/v1/genes/by-symbol/{symbol}?taxonomy_id=...` returns a gene with its locally associated protein summaries.
- `GET /api/v1/proteins/by-accession/{accession}` returns a protein with its organism and optional encoding gene.
- Existing numeric-ID and collection contracts are preserved.
- `/gene/:symbol` and `/protein/:accession` provide consistent scientific detail layouts with overview, identifiers/record fields, relationships, provider links, and retrieval provenance.
- Entity tables link directly to detail pages. Loading and provider/API error states remain reusable and retryable.

No schema migration was required in Phase 2: the Phase 1 entity tables already contained the identifiers, source URL, retrieval timestamp, and relationship columns needed for bounded single-provider imports. Adding speculative history tables would not have improved current integrity.

## 20. Phase 2 verification record

Verified on the implementation host:

- [x] Ruff formatting and lint checks pass.
- [x] Strict mypy analysis passes for 46 application source files.
- [x] Fifteen backend tests pass, including mocked NCBI and UniProt payloads, required NCBI identification, rate-limit retry behavior, coordinate conversion, idempotent imports, gene/protein linking, and explicit identifier APIs.
- [x] ESLint and TypeScript checks pass.
- [x] Five frontend tests pass, including both entity detail views and relationship navigation.
- [x] The Vite production build succeeds.
- [x] FastAPI and Vite start together against a disposable SQLite smoke database.
- [x] Health, paginated collections, both identifier routes, gene-to-protein linkage, protein-to-gene linkage, and the SPA detail route return successfully.
- [x] A manual read-only request to the live UniProt API normalized accession `P04637`, taxonomy `9606`, and sequence length `393` through the implemented adapter.
- [x] Existing Phase 1 tests and fixture behavior remain green.

Not executable on this host:

- [ ] Run `docker compose up --build`; Docker is not installed.
- [ ] Apply and exercise the Alembic migration against live PostgreSQL; no PostgreSQL service is available outside Docker.
- [ ] Perform a live NCBI adapter request; the project owner has not supplied the monitored contact email required by the adapter. Mocked contract tests cover the flow without misidentifying the caller.

SQLite smoke execution verifies application wiring only. PostgreSQL remains the configured source of truth and SQLite is not treated as evidence for PostgreSQL-specific runtime behavior.

## 21. Known limitations and technical debt after Phase 2

- Unified search is still a transparent placeholder; Phase 3 will implement PostgreSQL ranking and matching.
- Record-level provenance cannot preserve multiple competing provider claims, prior import snapshots, provider releases, parser versions, payload checksums, or job history.
- The first NCBI ESummary genomic placement is used. Coordinates are normalized to one-based inclusive values, but assembly/accession metadata is not stored and alternate placements are not represented.
- NCBI Gene ingestion currently resolves exact symbol plus taxonomy only. Gene aliases, retired/merged GeneIDs, batch imports, transcripts, and isoforms are out of scope.
- UniProt ingestion imports the canonical entry-level function and sequence length. Isoforms and additional annotation/evidence structures are not persisted.
- Protein imports do not automatically trigger gene imports. Import order can therefore temporarily leave `gene_id` null until the protein is refreshed.
- Provider imports are synchronous single-record CLI operations. Bulk scheduling, resumability, job status, and distributed rate management belong to Phase 8.
- Mutation endpoints remain unauthenticated and intended for controlled development use.
- PostgreSQL integration and migrations need Docker-capable CI coverage; isolated automated persistence tests use SQLite.
- There is no selected open-source license, CI pipeline, metrics, backups, production proxy, or deployment configuration.

## 22. Phase 3 implementation record

### Search data flow and ranking

```text
Shareable browser query /search?q=TP53&type=protein&page=1
    -> typed frontend client
    -> GET /api/v1/search
    -> SearchService
    -> bounded SQLAlchemy UNION ALL of Gene, Protein, Organism queries
    -> PostgreSQL
    -> typed results, category counts, provenance, matched fields, detail URLs
```

`SearchService` normalizes whitespace, rejects blank or overlong queries, escapes `ILIKE` wildcard characters, and uses bound SQL values. PostgreSQL combines case-insensitive partial/multi-term matching with `websearch_to_tsquery('simple', ...)` over entity-specific full-text documents. Exact stable identifiers receive the highest base score, followed by exact gene symbols/primary names, prefixes, related gene symbols, and remaining partial matches. A capped full-text rank refines results without allowing prose relevance to overtake an exact identifier. Equal-score provider records precede demo fixtures; stable label/type/ID tie-breakers make pagination deterministic.

Three per-entity count queries provide category totals; the selected category counts are summed for `total`, avoiding a redundant union count. The ranked union is limited and offset in the database. Suggestions reuse the ranked union with a small limit but skip count queries. Search returns only existing local records, including explicitly marked demo fixtures. The response carries record-level `source` and matched field excerpts. It does not assert new scientific relationships.

The `20260920_0002` migration enables `pg_trgm` and adds GIN trigram indexes for names/identifiers plus expression GIN indexes for `simple` full-text documents. Query expression field order and literal configuration match those indexes; a compilation test guards against accidental drift. PostgreSQL is the production search path. Isolated SQLite tests exercise the partial-match fallback, but do not claim to validate PostgreSQL ranking or index plans.

### API and frontend

`GET /api/v1/search` has a typed paginated response with `items`, `counts`, `total`, `pages`, `score`, `matched_fields`, provenance source, and stable detail URLs. `type` may be repeated; it filters the current result set without hiding other category counts. `GET /api/v1/search/suggestions` returns a bounded suggestion list. `/api/search` is a hidden compatibility alias for the requested unversioned shape; the versioned path is the documented contract. Blank input is rejected with the existing validation error envelope.

The frontend keeps query, entity filter, and page in the URL. Search cards show category, organism, matched fields, and provider/demo provenance. Highlighting is React-rendered text plus `<mark>`, never injected HTML. Gene links include taxonomy context to disambiguate symbols across organisms; the gene detail page reads this context, while existing bare gene links retain the human default. Organism results are shown without a detail link until an organism page is implemented. Loading, empty, and retryable failure states are explicit.

## 23. Phase 3 verification record

- [x] Twenty-one backend tests pass, including ranking, identifiers, filters, counts, pagination, suggestions, wildcard escaping, validation, and PostgreSQL SQL expression compilation. Existing Phase 1/2 tests remain green.
- [x] Eight frontend tests pass across entity pages, search results, highlighting, filters, suggestions, and retry/empty behavior.
- [x] Ruff formatting/lint, strict mypy, ESLint, Prettier, TypeScript, and the Vite production build pass.
- [x] FastAPI and Vite run against a disposable SQLite smoke database; health, search, suggestions, category filtering, gene lookup, and SPA route return successfully.
- [x] Read-only PostgreSQL 17 checks confirm migration revision `20260920_0002`, all twelve search indexes, and live ranked search for `TP53`, `P04637`, `7157`, `Homo sapiens`, and `tumor protein`.
- [x] Alembic generates valid PostgreSQL upgrade SQL through head.
- [ ] A fresh `docker compose up --build`, fresh PostgreSQL migration, and realistic-corpus performance test were not run from the implementation shell; the Docker CLI was unavailable there.

## 24. Known limitations and technical debt after Phase 3

- Search is local and limited to genes, proteins, and organisms. It does not yet provide aliases, synonym expansion, fuzzy typo correction, or semantic search.
- Rank weights are hand-selected and have not been evaluated against a curated relevance set. The live PostgreSQL check used a small development database, not a representative corpus.
- Three count queries and offset pagination are appropriate for the current scale but need profiling before claiming million-record performance. `ILIKE` on long descriptions/functions can still be expensive for certain partial queries.
- Organism results have no detail page. Bare gene URLs still default to human taxonomy for backward compatibility.
- Record-level provenance does not capture claims from multiple providers. The Phase 2 ingestion and security limitations recorded above still apply.
- PostgreSQL migration/index behavior needs repeatable fresh-database CI coverage; the automated persistence suite remains SQLite-isolated.

## 25. Phase 4 implementation record

### Entities and relational assertions

`Disease` stores name, description, optional MONDO/Disease Ontology identifiers, and record-level provenance. `Variant` stores an rsID and/or HGVS expression, organism, description, and record-level provenance. Database constraints enforce stable-identifier uniqueness and require at least one variant identifier; Pydantic applies matching request validation. Disease names are unique in the current canonical table; synonyms and ontology merges are not yet modeled.

Four explicit tables implement only predicates the platform can validate:

| Table | Subject → predicate → object | Integrity and provenance |
| --- | --- | --- |
| `gene_disease_associations` | Gene → associated_with → Disease | Endpoint FKs; unique endpoints + source + source identifier |
| `variant_gene_locations` | Variant → located_in → Gene | Endpoint FKs; same-organism service validation; source uniqueness |
| `variant_disease_associations` | Variant → associated_with → Disease | Endpoint FKs; source uniqueness |
| `protein_interactions` | Protein ↔ interacts_with ↔ Protein | Canonically ordered IDs (`a <= b`), including self/cross-organism interactions; source uniqueness |

Each assertion owns `source`, a required `source_identifier`, optional `source_url`, `evidence_text`, `imported_at`, and created/updated timestamps. Foreign keys restrict deletion. This is not a generic subject/predicate/object EAV table: columns and constraints encode the permitted entity types. The existing `protein.gene_id` remains the one-to-many `Gene → encodes → Protein` link; the relationship API projects it with `provenance_basis=protein_record` rather than manufacturing an independent evidence row. New associations use `provenance_basis=relationship_assertion`.

No disease or variant scientific facts are seeded by default. Their API writes require the caller to supply provenance. Phase 4 does not scrape free text or silently turn co-occurrence into an association. NCBI/UniProt ingestion and Phase 3 search remain unchanged; dedicated disease/variant provider adapters are deferred until source schemas and claim semantics can be validated.

### Relationship query and API

`RelationshipService` validates endpoints and organism-scoped variant locations, canonicalizes protein pairs, and translates unique-constraint conflicts. Gene and variant organism changes are refused while dependent links would make them inconsistent. The service builds a small `UNION ALL` index over the relation tables incident to the requested entity plus existing encoding links, counts and paginates in PostgreSQL, then batch-loads only the selected page's typed records with related nodes. Results have deterministic timestamp/type/ID ordering and typed subject/object URLs. The maximum page size is 100; there is no unbounded graph traversal.

`GET /api/v1/relationships/{entity_type}/{entity_id}` returns a typed page for a gene, protein, variant, or disease. Four explicit POST routes create the corresponding assertions; entity list/detail/create/patch and identifier lookup routes follow existing `/api/v1` conventions. All failures use the existing error envelope. These write endpoints are still unauthenticated and intended for controlled development only.

### Frontend

Diseases and Variants have paginated browsers and consistent detail pages. The reusable relationship panel appears on gene, protein, disease, and variant pages and shows node links, predicate, source label/identifier, optional evidence and provider link, and whether an encoding link inherited record provenance. Empty states do not imply any unseen scientific connection. The search engine remains limited to its Phase 3 entity types.

## 26. Phase 4 verification record

- [x] Twenty-four backend tests pass, including all prior-phase tests, new entity validation, typed edge creation, duplicate/reversed assertions, provenance, cross-entity browsing, pagination, organism integrity, self-interactions, and cross-organism protein interactions.
- [x] Eleven frontend tests pass, including disease/variant pages, sourced relationship navigation, and an honest empty state.
- [x] Ruff, strict mypy, ESLint, Prettier, TypeScript, and the production Vite build pass.
- [x] PostgreSQL 17 upgrades `20260921_0003` and `20260921_0004` applied successfully; Alembic reports head and no pending schema operations.
- [x] Live FastAPI and Vite smoke checks against PostgreSQL returned health, empty disease/variant collections, an existing gene→protein edge, Phase 3 search, OpenAPI version `0.4.0`, and both new SPA routes.
- [x] Offline PostgreSQL migration SQL compiles through head. Automated provider tests remain network-independent.
- [ ] Fresh Docker Compose build, fresh-database migration replay, and representative large-corpus relationship query plans remain for CI; the Docker CLI was unavailable in this shell.

## 27. Known limitations and technical debt after Phase 4

- Disease and variant ingestion is not automated; MONDO/ClinVar/dbSNP adapters need provider-specific normalization and source/evidence policy before adoption. The new collections are empty on fresh startup by design.
- Assertions carry a source and optional evidence text, not a confidence score or scientific validation. Field-level claim conflicts, ontology aliases, clinical significance, genome assembly, variant normalization, and evidence ontologies are not modeled.
- Existing gene→protein links inherit protein-record provenance. They do not have separate relationship assertion history.
- The UI reads new entities and edges but does not create them; writes are API-only and unauthenticated. Production authorization is deferred to hardening.
- Same-organism variant→gene integrity is enforced in application services rather than a cross-table database constraint. Direct database writes could bypass it.
- Offset pagination and the union-based relationship listing need performance testing on a large real dataset. No graph-depth traversal is exposed in Phase 4.
- A downgrade from `20260921_0004` to `20260921_0003` cannot succeed while self-protein interaction rows exist, because the older check constraint rejects them; no data is automatically deleted.
- Phase 2 provider-ingestion and Phase 3 search limitations recorded above remain applicable. There is still no CI, rate limiting, production deployment, or selected open-source license.

## 28. Phase 5 boundary

Phase 5 may add publications, literature metadata ingestion, citation links, publication search, and evidence-linked relationships to biological entities. Structured provider relationships must be distinguished from any future NLP-extracted mentions or hypotheses. Publications have not been implemented in Phase 4.

## 29. Architecture maintenance

This document is updated in every phase to describe the system that actually exists. Planned sections must stay visibly distinguished from implemented behavior. Material architectural changes should record the decision, trade-off, and trigger that justified it rather than silently replacing working conventions.
