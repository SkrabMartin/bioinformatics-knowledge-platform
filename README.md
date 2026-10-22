# Bioinformatics Knowledge Platform

An open-source-oriented web platform for aggregating, searching, and exploring biological knowledge across genes, proteins, organisms, diseases, variants, publications, and—over time—pathways, datasets, and other biomedical entities.

The long-term product combines a biological knowledge graph, scientific search engine, database browser, and research dashboard while keeping imported information traceable to its source.

## Project status

**Phase 5 — Publications and Scientific Literature is implemented (0.5.0, work in progress).**

The platform imports NCBI genes, UniProt proteins, and PubMed citations. Unified search covers locally stored genes, proteins, organisms, and publications. Explicit relationship tables preserve referential integrity and source context for biological and literature assertions. Publication pages offer citations, available abstracts, authors, partial publication dates, and links to related records. Previous entity APIs and development fixtures are preserved.

The application still ships explicitly marked Phase 1 demo fixtures for local startup. Real gene/protein imports are opt-in CLI operations. Phase 4 does **not** automatically import disease or variant assertions: those collections start empty until source-backed records are supplied through the API. Search never invents results for absent records.

Current architecture, Phase 5 operation, and verification notes are maintained in this README. [ARCHITECTURE.md](ARCHITECTURE.md) and [CHANGELOG.md](CHANGELOG.md) retain the historical Phase 0–4 design and change records.

## What works

- FastAPI application with OpenAPI documentation, CORS, structured logging, request IDs, and normalized errors.
- SQLAlchemy models and Alembic migrations for `Organism`, `Gene`, `Protein`, `Disease`, `Variant`, and `Publication`.
- Paginated list, detail, create, and update APIs; hard deletion is deliberately omitted.
- Idempotent loader for clearly labeled, non-authoritative Phase 1 fixtures.
- NCBI Gene and UniProtKB adapters with typed normalization, timeouts, bounded retries, rate-limit handling, and safe failures.
- Idempotent single-record gene and protein import commands with stable-identifier matching and record-level provenance.
- Idempotent PubMed citation import by PMID, safe bounded XML parsing, normalized DOI identity, and explicit NCBI `pubmed_gene` links to genes already stored locally.
- PostgreSQL-backed unified search with exact-identifier weighting, partial and multi-term matching, per-type counts, filters, deterministic ranking, pagination, and debounced suggestions.
- Typed, provenance-bearing gene–disease, variant–gene, variant–disease, and protein–protein assertions; the existing gene→protein link is exposed with protein-record provenance.
- Paginated relationship APIs and new disease/variant list and detail pages; connected entity pages link to sourced relations.
- React/TypeScript application with Home, Search, Genes, Proteins, Diseases, Variants, Publications, detail, About, and not-found pages.
- Reusable navigation, search, cards, tables, pagination, loading, empty, and error states.
- Responsive scientific UI with explicit provenance badges and demo-data notices.
- Publication browsing/search, newest/oldest/relevance sorting, citation links, and an associated-publications section on gene pages.
- Fail-closed administrator token protection for new literature HTTP writes and a baseline GitHub Actions workflow with PostgreSQL migration/runtime checks.
- Docker Compose services for PostgreSQL, backend, and frontend.
- Backend and frontend tests plus lint, formatting, typing, and build checks.

## Architecture at a glance

```text
Browser
  |
  v
React + TypeScript frontend
  |
  v
FastAPI REST API
  |
  v
Service layer
  |
  v
Repository layer
  |
  v
PostgreSQL
```

Data ingestion follows a separate implemented boundary:

```text
External biological APIs
  |
  v
Provider adapters
  |
  v
Normalization and validation
  |
  v
Ingestion services
  |
  v
PostgreSQL
```

Phase 4 relationships use explicit foreign-key tables rather than an unconstrained generic edge store:

```text
Gene ──associated_with──> Disease
Variant ──located_in──> Gene
Variant ──associated_with──> Disease
Protein <──interacts_with──> Protein
Gene ──encodes──> Protein (existing protein.gene_id)
```

Each new assertion stores its source, source identifier, optional source URL and evidence text, and timestamps. The inherited encoding link uses the protein record's provenance and is labeled as such in the API.

### Phase 5 architecture

```text
PubMed EFetch XML + ELink JSON
    -> bounded retrying HTTP transport (2 MB decompressed response limit)
    -> PubMed adapter + safe XML parser (defusedxml)
    -> provider-independent normalized citation
    -> PublicationIngestionService (one database transaction)
    -> PostgreSQL publications + publication_genes

React publication browser / gene page / unified search
    -> versioned FastAPI read API
    -> PublicationService + PublicationRepository / SearchService
    -> bounded PostgreSQL filtering, ranking, ordering and pagination

Administrator bearer token
    -> explicit publication link API
    -> PublicationService + RelationshipService
    -> publication_genes / publication_proteins / publication_diseases
```

`publications` stores unique nullable PMID/DOI identifiers (at least one required), title, optional abstract/journal, ordered author names as JSON, record provenance, and date metadata. `publication_date` is a validated ISO partial date (`YYYY`, `YYYY-MM`, or `YYYY-MM-DD`); `publication_date_text` retains the provider's date wording. No missing month/day is synthesized. Sorting uses the available partial ISO date, puts absent dates last, and uses the internal ID as a tie-breaker; ordering within an incompletely dated period does not establish the actual publication chronology.

Three explicit literature assertion tables have restrictive foreign keys, required source identifiers, source-scoped uniqueness, and `evidence_kind=structured_metadata|curated`. Publication→gene uses `mentions`, publication→protein `discusses`, and publication→disease `studies`. These are source assertion labels, not confirmation of causality, clinical validity, or independently reviewed evidence. The UI displays their acquisition kind. No NLP extraction or automatic disease/protein claims are implemented.

The adapter imports one journal-style `PubmedArticle` citation, then reads its explicit `pubmed_gene` ELink records. Only matching local NCBI Gene IDs become edges; no partial genes are manufactured. A failure of either upstream request aborts the import before persistence. Reimporting updates citation metadata and retrieval times, adds missing supported links, and rejects PMID/DOI identity conflicts without merging records. A temporarily absent DOI does not erase an established DOI. Links removed by a provider are not automatically retired in this phase.

Publication SQL matching is shared by the publication repository and unified search. Exact PMID/DOI matches receive high relevance. The additive `20261022_0005` migration creates the four tables plus full-text GIN and title-trigram indexes. Its full-text expression is mirrored in ORM metadata and covered by PostgreSQL compilation/runtime tests; Alembic excludes the expression index from unreliable textual comparison, as it already does for earlier entity indexes.

New HTTP link writes use `BKP_ADMIN_API_TOKEN` on the server. With no configured token they return `503`; missing or incorrect credentials return `401`. This is scoped protection for the new operations, not authentication for the entire legacy API. CLI imports rely on local operating-system access. No admin token is sent to the browser or stored in frontend configuration.

## Repository layout

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── ingestion/
│   │   ├── integrations/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── search/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── cli.py
│   │   ├── fixtures.py
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── test/
│   │   └── types/
│   └── package.json
├── data/
│   ├── fixtures/
│   ├── processed/
│   └── raw/
├── .env.example
├── docker-compose.yml
├── ARCHITECTURE.md
├── CHANGELOG.md
└── README.md
```

`backend/app/search/` owns ranking and result assembly; the API router only validates requests and returns typed responses.

## Quick start with Docker Compose

Requirements:

- Docker with Docker Compose support
- ports `5173`, `8000`, and `5432` available

Create a local environment file and start the stack:

```bash
cp .env.example .env
docker compose up --build
```

On PowerShell, use `Copy-Item .env.example .env` instead of `cp`.

Before running NCBI imports, replace `researcher@example.org` in `.env` with a monitored contact address. NCBI requests include the configured tool name and email; an API key is optional. Do not commit the resulting `.env` file.

The backend container explicitly runs the Alembic migration and idempotent development fixture loader before starting the API. The application does not run migrations as an import or hidden startup side effect.

Open:

- frontend: <http://localhost:5173>
- API documentation: <http://localhost:8000/docs>
- health endpoint: <http://localhost:8000/api/health>

Stop the stack with `docker compose down`. Add `--volumes` only when intentionally discarding the development database.

### Frontend dependency-volume recovery

The frontend installs its locked dependencies into the Linux `frontend_node_modules` volume before starting Vite. If that volume was created by an older Compose configuration and remains corrupt, recreate only the frontend dependency volume without deleting PostgreSQL data:

```powershell
docker compose stop frontend
docker compose rm -f frontend
docker volume ls --filter name=frontend_node_modules
```

Remove the exact frontend dependency volume name shown by the last command, then restart with `docker compose up --build`. Do not run `docker compose down --volumes` unless the PostgreSQL development data should also be deleted.

## Native development

### Backend

Python 3.12 and PostgreSQL are required. From the repository root:

```bash
python -m venv .venv
```

Activate the environment, then run:

```bash
python -m pip install -e "backend[dev]"
alembic -c backend/alembic.ini upgrade head
python -m app.cli load-fixtures
uvicorn app.main:app --app-dir backend --reload
```

The default database URL expects PostgreSQL at `localhost:5432`. Override any setting with a `BKP_`-prefixed environment variable. Settings load the repository-root `.env` file automatically.

The fixture loader is idempotent. A second run reports zero created records.

### Import real records

Apply migrations first, configure `BKP_NCBI_EMAIL`, then run imports from the repository root with the backend package installed:

```bash
python -m app.cli import-gene TP53
python -m app.cli import-gene BRCA1 --taxonomy-id 9606
python -m app.cli import-protein P04637
python -m app.cli import-publication <PMID>
```

Each command prints a JSON result containing the internal entity ID and an action of `created`, `updated`, or `unchanged`. Repeating an import refreshes the matched row instead of inserting a duplicate. For the best gene–protein linkage, import a gene before its protein; a later protein re-import will add the link when NCBI GeneID or the organism-scoped symbol matches.

Provider failures do not fall back to invented data. The CLI exits non-zero with a safe JSON error when configuration is missing, a record is absent, a response is malformed, rate limits remain exhausted, or the provider is unavailable.

### Import and read literature

Replace `<PMID>` with a real positive numeric PubMed ID. PubMed imports require a monitored `BKP_NCBI_EMAIL`; the example placeholder is rejected. EFetch retrieves citation metadata and the available abstract; ELink retrieves explicit provider gene links. The adapter spaces its two requests conservatively and uses existing timeout/retry policies. This is a bounded single-record command, not a bulk crawler or background import system. Independent concurrent CLI processes do not share a global rate limiter.

With Docker Compose:

```bash
docker compose exec backend python -m app.cli import-publication <PMID>
```

Open <http://localhost:5173/publications>, search by title, abstract, journal, PMID or DOI, and choose Newest, Oldest or Relevance. Query, sort, page and optional `gene_id` filters are stored in the URL. `/publication/{id}` shows available source metadata, date precision, external PubMed/DOI links and stored relationships. Gene pages show their five newest linked citations and link to the full filtered collection. Import the gene first, or reimport the citation later, to establish links to newly available local genes.

No publications are seeded by default. A fresh installation shows an honest empty collection until an import succeeds. An absent abstract, author list or date remains visibly absent. PubMed metadata/abstract availability and reuse conditions depend on the source; this phase does not download full-text papers. See the [NCBI PubMed XML documentation](https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/index.html) and [NCBI usage guidance](https://www.ncbi.nlm.nih.gov/home/about/policies/).

To add a source-backed literature assertion manually, configure a strong server-only `BKP_ADMIN_API_TOKEN`, restart the backend, and authorize the operation in <http://localhost:8000/docs> using a bearer token. `POST /api/v1/publications/{id}/links/{gene|protein|disease}` accepts `entity_id`, required `source` and `source_identifier`, required `evidence_kind` (`curated` or `structured_metadata`), and optional URL/evidence/retrieval metadata. Use only source-supported assertions. Identical endpoint/source/source-ID assertions return `409`; missing endpoint records return `404`. The read-only GUI does not collect administrator credentials.

### Search the application

Open <http://localhost:5173/search>, type `TP53`, `P04637`, `7157`, a publication PMID/DOI, or an organism name, and press Search. Results are drawn only from records already in the database; importing a real record makes it searchable. Use the Genes, Proteins, Organisms, or Publications filter to narrow results. The URL (`/search?q=TP53&type=protein&page=2`) can be shared or bookmarked. Search suggestions appear as you type and link to matching records.

An exact accession or external ID ranks above prefix and partial matches. Gene-symbol matches rank above related proteins for the same query. Matched fields and provider/demo provenance are shown on each result card. Organisms have search results but no organism detail page yet; gene and protein results open their Phase 2 detail pages. For non-human genes, search links carry the organism taxonomy ID to resolve the correct symbol.

### Explore diseases, variants, and relationships

Open <http://localhost:5173/diseases> or <http://localhost:5173/variants>. The lists are empty on a fresh installation because Phase 4 ships no invented disease/variant facts. Records can be added through the documented API with a real source and stable source identifier; use `source=development_fixture` and an explicit demo identifier only for test/demo data. On gene, protein, disease, and variant detail pages, the Relationships section shows stored assertions, evidence text, source identifiers, and links to connected records. No relationship is inferred from a matching name or free-text description.

The API has no authentication yet. Do not expose development write endpoints to untrusted networks or submit unsupported scientific claims. Existing gene→protein links are shown with `provenance_basis=protein_record`; new association rows use `provenance_basis=relationship_assertion`.

### Frontend

Node.js 22 or newer and pnpm are required. From `frontend/`:

```bash
pnpm install
pnpm dev
```

Set `VITE_API_BASE_URL` when the API is not available at `http://localhost:8000/api/v1`.

## API

Operational endpoint:

```text
GET /api/health
```

Versioned resources:

```text
GET   /api/v1/organisms
POST  /api/v1/organisms
GET   /api/v1/organisms/{id}
PATCH /api/v1/organisms/{id}

GET   /api/v1/genes
POST  /api/v1/genes
GET   /api/v1/genes/by-symbol/{symbol}?taxonomy_id=9606
GET   /api/v1/genes/{id}
PATCH /api/v1/genes/{id}

GET   /api/v1/proteins
POST  /api/v1/proteins
GET   /api/v1/proteins/by-accession/{accession}
GET   /api/v1/proteins/{id}
PATCH /api/v1/proteins/{id}

GET   /api/v1/search?q=TP53&page=1&page_size=20
GET   /api/v1/search/suggestions?q=TP&limit=8

GET   /api/v1/publications?q=...&sort=newest&page=1&page_size=20
GET   /api/v1/publications?gene_id={gene_id}
GET   /api/v1/publications/{id}
POST  /api/v1/publications/{id}/links/{gene|protein|disease}  (administrator bearer token)

GET   /api/v1/diseases
POST  /api/v1/diseases
GET   /api/v1/diseases/by-mondo/{mondo_id}
GET   /api/v1/diseases/{id}
PATCH /api/v1/diseases/{id}

GET   /api/v1/variants
POST  /api/v1/variants
GET   /api/v1/variants/by-rsid/{rsid}
GET   /api/v1/variants/{id}
PATCH /api/v1/variants/{id}

GET   /api/v1/relationships/{gene|protein|variant|disease|publication}/{id}
POST  /api/v1/relationships/gene-disease
POST  /api/v1/relationships/variant-gene
POST  /api/v1/relationships/variant-disease
POST  /api/v1/relationships/protein-interaction
```

Collection endpoints accept one-based `page` and bounded `page_size` parameters. The response includes `items`, `page`, `page_size`, `total`, and `pages`.

Search accepts a non-blank query of at most 200 characters, `page_size` from 1 to 100, and repeated `type=gene|protein|organism|publication` parameters. Its response also includes per-category counts, relevance scores, matched fields, source labels, and detail links. Counts cover all categories even when `type` filters the current page; `total` and `pages` describe the selected categories. Suggestions require at least two characters and return at most 12 records. `/api/search?q=...` is a compatibility alias; `/api/v1/search` is the documented canonical endpoint. Publication collection reads additionally accept `sort=newest|oldest|relevance`, optional `q`, and optional `gene_id`; relevance without a query falls back to newest available dates.

Disease records may carry MONDO and Disease Ontology IDs. Variants require an rsID or HGVS expression and an organism. Every new relationship assertion requires `source` and `source_identifier`; optional `source_url`, `evidence_text`, and `imported_at` retain additional context. The relationship response has typed `subject`, `predicate`, and `object` nodes plus `provenance_basis`. Relationship lists are paginated in the database. Repeated assertions from the same source and source identifier return `409`; protein interaction endpoint order is canonicalized so reversed pairs cannot bypass uniqueness. Self-interactions and cross-organism protein interactions are allowed. Variant→gene location links require the same organism.

Expected failures use a consistent envelope:

```json
{
  "error": {
    "code": "gene_not_found",
    "message": "Gene 123 was not found.",
    "details": null,
    "request_id": "correlation-id"
  }
}
```

## Development fixtures

`data/fixtures/phase1_demo.json` contains a small set of UI and API examples. Every fixture uses `source=development_fixture`; identifiers are prefixed with `demo-` or `DEMO-`, and descriptions state that the data is not authoritative.

Do not use these records for scientific analysis. Real imports replace matching fixture entities with provider-backed values where stable identity can be established; unrelated demo records remain clearly labeled.

## Quality checks

Backend, from `backend/` with the root virtual environment active:

```bash
python -m ruff format --check app tests migrations
python -m ruff check app tests migrations
python -m mypy app
python -m pytest
python -m alembic upgrade head --sql
python -m alembic check
```

Frontend, from `frontend/`:

```bash
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

The Phase 4 verification run passed 24 backend tests and 11 frontend tests, Ruff, strict mypy, ESLint, Prettier, TypeScript, and the production frontend build. The additive PostgreSQL migrations `20260921_0003` and `20260921_0004` were applied to the reachable development database; Alembic reports head and no pending schema operations. Live FastAPI and Vite processes passed health, disease/variant collection, existing gene→protein relationship, search, OpenAPI-version, and SPA-route checks against PostgreSQL. Automated scientific-provider tests remain network-independent.

The preceding paragraph records the historical Phase 4 checks. Phase 5 adds a GitHub Actions baseline for backend lint/format/typing/tests, clean PostgreSQL migrations and schema comparison, plus frontend lint/format/typing/tests/build. Automated provider tests use mocked responses; the PostgreSQL runtime test is opt-in locally via `BKP_TEST_POSTGRES_URL` and enabled in CI against its disposable database. Local SQLite tests remain useful but do not substitute for that PostgreSQL check.

### Phase 5 verification and change record (2026-10-22)

- 40 backend tests passed, including all three literature link types and the opt-in PostgreSQL 17 publication migration/full-text runtime check; earlier-phase regression tests passed.
- 17 frontend tests passed; Ruff, mypy, ESLint, Prettier, TypeScript and the production Vite build passed.
- All five migrations replayed successfully on a fresh isolated PostgreSQL 17 database; Alembic reports no pending model/schema differences.
- A manual live PubMed import succeeded through the implemented EFetch/ELink adapter into the isolated verification database. Automated tests remain independent of this provider.
- Docker built both application images with their declared dependencies. The default host port 5432 was already allocated, so the full stack ran successfully in an isolated Compose project with alternate host ports. Its fresh database migrated successfully; API health/version, previous gene search, publication browser/detail/search, relationships, and frontend SPA responses passed live HTTP checks. A real PubMed import in that stack returned `created`, then `unchanged` on repetition.
- An upstream Starlette/AnyIO deprecation warning remains in the local test environment. Production-scale query performance and remote CI execution are separate from the local checks.

Important Phase 5 files: `backend/app/models/publication.py`, `schemas/publication.py`, `repositories/publications.py`, `services/publications.py`, `integrations/ncbi/pubmed.py`, `ingestion/publications.py`, `search/publications.py`, `api/v1/publications.py`, `core/security.py`, migration `20261022_0005_publications.py`, the publication tests, frontend publication pages/components, and `.github/workflows/ci.yml`.

## Product principles

- Never fabricate scientific data. Development fixtures are visibly labeled.
- Preserve provenance so imported information can be traced to a provider and source identifier.
- Keep provider response formats behind adapters and normalization boundaries.
- Prefer a modular monolith until operational evidence justifies more infrastructure.
- Paginate and filter in the database rather than loading entire collections into memory.
- Treat migrations, tests, documentation, and observable failures as part of the product.
- Add complexity only when it supports a working phase.

## Known limitations

- Disease and variant records, and their associations, are API-created only in Phase 4. There is no automated MONDO, ClinVar, or dbSNP ingestion yet; a fresh installation shows empty disease/variant collections rather than made-up science.
- Relationship evidence is source-level assertion metadata, not a scientific confidence score or independently verified claim. Curated versus machine-extracted assertions and multi-source claim reconciliation are not modeled.
- Existing gene→protein linkage inherits protein-record provenance; it has no separate relationship-evidence row. Clinical significance, assembly-aware coordinates, variant normalization, and evidence ontologies are not stored.
- The relationship listing uses bounded offset pagination. Large-corpus query plans and association counts have not been benchmarked. Cross-organism integrity for variant→gene links is enforced by services, not a cross-table database constraint.
- The UI is read-only for disease/variant and relationship creation; controlled-development writes use the API. Write endpoints remain unauthenticated and must not be internet-exposed.
- Search covers locally stored genes, proteins, organisms, and publications. Diseases/variants are not yet part of unified search. There is no fuzzy typo correction, synonym expansion, alias handling, or cross-provider federated search.
- Search uses offset pagination and synchronous count queries. Ranking weights and PostgreSQL index use have not been benchmarked on a large biological corpus.
- Organism results have no detail page yet. Gene search links require taxonomy context; older bare `/gene/{symbol}` links still default to human (`9606`).
- There are no hard-delete endpoints or entity deprecation workflow yet.
- Entity provenance is record-level and relationship assertions have their own source fields. Multiple-provider claim history, raw payload retention, payload checksums, provider releases, parser versions, and import-job history are not yet modeled.
- NCBI Gene summary coordinates are converted from zero-based positions to one-based inclusive coordinates, but the selected assembly/accession is not stored yet; the first provider placement is used.
- Gene imports require a configured NCBI contact email. Phase 4 verification did not depend on live NCBI requests; its adapter remains covered by mocked contract tests.
- Protein imports link only to genes already present locally and do not synthesize partial genes from UniProt data.
- Publication imports support journal-style PubMed article records, not book citations, full texts, provider deletion feeds, retraction-status tracking, or corrected identity reconciliation. Author names are ordered text values, not researcher/ORCID entities. DOI is canonicalized and format-validated, not independently resolved.
- Literature links come from explicit provider metadata or controlled source-backed API entry. A gene mention is not evidence of a causal association; no NLP extraction or automated protein/disease literature linking is implemented.
- Source record/history reconciliation and stale-link retirement remain deferred. Partial publication dates preserve precision but cannot establish exact ordering within unknown periods.
- New literature writes require an administrator token; existing Phase 1–4 write endpoints remain unauthenticated. The complete application is still intended for controlled development use.
- There is a baseline CI pipeline, but rate limiting, metrics, backup automation, comprehensive authorization, and production deployment configuration are still deferred.
- An open-source license has not yet been selected, so reuse terms are not established.

## Next phase

Phase 6 will add an interactive knowledge graph explorer with bounded depth/node/edge counts, source inspection, expansion/collapse, and navigation to entity pages. It has not been implemented as part of Phase 5.

Graph traversal, pathways, OpenSearch/Elasticsearch, and later-phase infrastructure remain out of scope.

## Contributing

1. Keep changes within the active phase.
2. Include tests for behavior changes.
3. Add migrations for schema changes; never rewrite applied migration history.
4. Keep external payloads outside domain and persistence interfaces.
5. Update `README.md`, `ARCHITECTURE.md`, and `CHANGELOG.md` when behavior or architecture changes.

## License

A license has not yet been selected. The project intends to be open source, but distribution and reuse terms are not established until a `LICENSE` file is added.
