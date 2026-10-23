# Bioinformatics Knowledge Platform

An open-source-oriented web platform for aggregating, searching, and exploring biological knowledge across genes, proteins, organisms, diseases, variants, publications, and—over time—pathways, datasets, and other biomedical entities.

The long-term product combines a biological knowledge graph, scientific search engine, database browser, and research dashboard while keeping imported information traceable to its source.

## Project status

**Phase 7 — Pathways, Ontologies and Advanced Bioinformatics is implemented (0.7.0, work in progress).**

The platform imports NCBI genes, UniProt proteins, and PubMed citations. Unified search covers locally stored genes, proteins, organisms, and publications. Explicit relationship tables preserve referential integrity and source context for biological and literature assertions. Publication pages offer citations, available abstracts, authors, partial publication dates, and links to related records. Previous entity APIs and development fixtures are preserved.

The application still ships explicitly marked Phase 1 demo fixtures for local startup. Real gene/protein imports are opt-in CLI operations. Phase 4 does **not** automatically import disease or variant assertions: those collections start empty until source-backed records are supplied through the API. Search never invents results for absent records.

The interactive graph explorer now navigates stored gene, protein, disease, variant, and publication assertions with bounded traversal, node expansion, branch collapse, and source inspection. It does not infer missing relationships or treat source assertions as confirmed scientific conclusions.

Pathways and GO biological-process/molecular-function terms now extend that navigation with direct, source-backed annotations and `is_a` hierarchies. Functional collections start empty and are populated through protected administrator APIs. Statistical enrichment and automatic GO/pathway ingestion are not implemented. The home page replaces its decorative entity diagram with a live local-record starting point, provenance, a graph link and a brief research workflow.

Current architecture, operation, and verification notes are maintained in this README. [ARCHITECTURE.md](ARCHITECTURE.md) and [CHANGELOG.md](CHANGELOG.md) retain the historical Phase 0–4 design and change records.

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
- Interactive Cytoscape.js graph with pan/zoom, typed nodes, directed assertions, provenance inspection, bounded expansion/collapse, shareable query settings, and entity-page navigation.
- Pathway/GO browsers and detail pages; direct gene→pathway, gene→biological-process, protein→molecular-function annotations, and same-aspect multi-parent `is_a` assertions with source releases.
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

### Phase 6 architecture

```text
Graph page / entity relationship panel
    -> typed, read-only graph REST API
    -> GraphService: bounded breadth-first traversal and response assembly
    -> GraphRepository: limited UNION projections over eight existing relationship kinds
    -> PostgreSQL typed relationship tables (no new tables or migration)

Graph response -> bounded client workspace -> lazy-loaded Cytoscape.js canvas
                                        -> keyboard-accessible node/edge inspector
```

The graph reuses all five Phase 4 relationship kinds and the three literature link kinds. Each node has a type-qualified ID, detail-page link, and discovery depth. Each edge has a relationship-kind-qualified ID and the complete existing assertion/provenance response. Multiple sources remain separate edges; self-interactions are retained. Encoding edges inherit protein-record provenance. Protein interactions are undirected; other assertions retain their semantic arrow even though neighborhood discovery follows incoming and outgoing links.

Traversal defaults to depth 1, 60 nodes and 120 edges; hard maximums are depth 3, 150 nodes and 300 edges. At most 1,000 candidate edges are scanned per request. Each table projection is limited before the combined result is limited; only selected records are hydrated. A final bounded pass adds edges between already discovered boundary nodes without going beyond the requested depth. Filters do not traverse hidden entity types; the root always remains visible. Ordering is deterministic for unchanged data, not scientific relevance ranking.

`BKP_GRAPH_TIMEOUT_MS` defaults to 1500 (allowed range 100–10000). Cooperative checkpoints bound traversal work, and every PostgreSQL graph SQL statement receives the remaining transaction-local statement timeout. The listener is detached before cancellation rollback and on exit. A timeout before loading the root returns normalized `503 graph_timeout`; afterward it returns the completed partial neighborhood with `time_budget`. This is not a hard end-to-end HTTP deadline: database connection checkout, response serialization and network transport are outside that budget.

Responses expose `truncated`, `truncation_reasons` (`node_limit`, `edge_limit`, `scan_limit`, `time_budget`, or `data_changed`), and `scanned_edges`. Missing/deleted or changed projected endpoints are skipped safely. Reads do not establish a frozen multi-query snapshot. A complete response describes only the stored neighborhood at the requested depth and filters, not complete biological knowledge.

The browser enforces the same workspace node/edge caps across successive one-hop expansions, deduplicates typed IDs, and never introduces dangling edges. Collapse prunes nodes no longer reachable from the root when traversal stops at the selected branch; nodes reachable by another route remain. Requests are aborted when query settings change or the page closes; expansion errors preserve the graph for retry. Cytoscape is loaded only for the graph page. No graph database, background workers, or new ingestion source is introduced.

### Phase 7 architecture

```text
Administrator API (existing server-only bearer token)
    -> KnowledgeService -> KnowledgeRepository / explicit ORM tables
    -> PostgreSQL identity, source uniqueness and aspect constraints

Pathway / process / function browser and detail
    -> paginated reads + shared RelationshipPanel
    -> existing GraphService / GraphRepository (same safety caps)
```

`pathways` has a source-scoped stable identifier, name/description, optional organism scope, required source release and provenance. `ontology_terms` has globally unique `GO:nnnnnnn` IDs, a validated aspect, and required source/release metadata. SQLAlchemy single-table inheritance exposes distinct `BiologicalProcess` and `MolecularFunction` domain models without duplicating GO identity across tables. Neither names nor GO numeric ranges establish aspect membership: administrators must supply source-backed metadata. Payload validation checks format, not independent scientific correctness.

Three explicit tables (`gene_pathways`, `gene_biological_processes`, `protein_molecular_functions`) store direct positive assertions, evidence kind/code, source identifier, release, optional evidence text/URL and retrieval timestamp. Composite foreign keys constrain process/function annotation targets to their correct aspect. Pathway membership validates organism compatibility when the pathway has a scope; API gene-organism updates use the same gene row lock and cannot invalidate an existing membership. Optional organism scope does not imply universal membership across species.

`ontology_parents` stores sourced direct child→`is_a`→parent assertions. Composite foreign keys prohibit cross-aspect links and a check constraint forbids self-parent edges. Multiple parents are allowed. Administrator writes reject cycles using a deduplicating recursive ancestor query with a 1,000-ancestor validation cap; larger validation requests fail closed. A nonblocking PostgreSQL transaction advisory lock serializes hierarchy mutations, so concurrent incompatible writes cannot both pass cycle validation under the default READ COMMITTED isolation. Cycles are prevented by the service, not a database-wide DAG trigger: direct SQL writers must not bypass this boundary.

The additive `20261023_0006` migration creates six indexed tables and leaves existing entities and assertions intact. Shared relationship responses add nullable `source_release` and `evidence_code` for compatibility; graph traversal now covers eight node types and thirteen relationship kinds, with unchanged depth/node/edge/time limits. `is_a` arrows point from specific to broader terms; neighborhood browsing follows both directions. No annotation propagation, inferred membership or relationship confidence scores are computed.

This is an enrichment-ready **data foundation**, not an enrichment engine: stable direct gene memberships, organism context and source releases can underpin a later explicit gene-set/background snapshot. No reference population, p-value, enrichment score or multiple-testing result is fabricated. A future calculation must specify its universe, identifier mapping, annotation propagation/evidence policy, source versions, statistical test and correction, and return reproducible results. Source releases are caller-supplied labels, not archived reproducible snapshots yet.

GO has distinct relation semantics and permits multiple parents; this phase deliberately supports only direct same-aspect `is_a` hierarchy. It does not reinterpret `regulates`, `part_of`, negative (`NOT`) annotations, obsolete terms, or cellular-component terms as positive annotations. Unknown payload fields are rejected. The application predicates `involved_in` and `has_function` are its scoped source-assertion labels, not a claim to implement every GO annotation relation. See the [GO relations documentation](https://geneontology.org/docs/ontology-relations/) and [GO annotation principles](https://www.geneontology.org/docs/go-annotations/).

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
│   │   ├── features/
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

### Explore the knowledge graph

Open <http://localhost:5173/graph>, enter a stored gene symbol (human taxonomy `9606` by default), or use **Explore graph** in an entity's Relationships section. A direct example is `/graph?symbol=TP53&taxonomy_id=9606`; typed internal IDs use `/graph?type=gene&id=1`. The default fixtures show a clearly marked demo encoding edge, not authoritative biological evidence.

Use the depth and node/edge controls and entity/relationship filters to bound the neighborhood. Pan by dragging the background, zoom with the wheel or buttons, and use Fit to return to the visible graph. Click a node or edge, or use the inspector's native selection controls, to inspect it. Nodes link to their entity pages and support one-hop expansion and branch collapse. Edges show predicate, source identifier, retrieval timestamp, evidence text/kind when available, provenance basis, and source links. Colors and shapes distinguish entity types.

The URL preserves the root, initial depth, limits, and filters. Manual node positions and expanded/collapsed workspace history are session-local. Partial-result warnings are intentional safety signals: lower depth, narrow filters, or change limits for a different view. An entity with no stored assertions shows an honest isolated-node state. Pathways, biological processes and molecular functions are now graph nodes with their own shapes and filters. Organisms remain outside the explicit graph relationships.

### Explore pathways and GO concepts

Open <http://localhost:5173/pathways>; the collection navigation also opens `/biological-processes` and `/molecular-functions`. Filter by name or stable identifier. Filter/page state is shareable in the URL. Record pages (`/pathway/{id}`, `/biological-process/{id}`, `/molecular-function/{id}`) show identifiers, source release, provenance, and direct relationships. Follow the existing graph link to explore direct parents, children or annotations. Gene and protein pages automatically show the new incident assertions in their Relationships section.

New installations intentionally contain no pathway or GO assertions. There is no automatic Reactome/GO import or default invented functional fixture. To enter source-backed records, configure `BKP_ADMIN_API_TOKEN` on the server and use the bearer authorization in API docs. Every new write requires that token; the read-only GUI never collects it. Omit an unknown organism scope rather than guessing it, and supply a genuine source release label. GO IDs are format-validated only; administrators remain responsible for correct labels/aspects and evidence. These APIs accept direct positive annotations only, not GAF/GPAD files or NOT annotations.

Example request shapes (replace placeholders with verified source values and local IDs):

```text
POST /api/v1/pathways
  name, source, source_identifier, source_release,
  optional description, organism_id, source_url, imported_at
POST /api/v1/ontology
  kind=biological_process|molecular_function, go_id=GO:nnnnnnn,
  name, source, source_identifier, source_release, optional description/source metadata
POST /api/v1/pathways/{id}/genes
POST /api/v1/ontology/{kind}/{id}/annotations
  entity_id (gene for pathway/process; protein for function),
  source, source_identifier, source_release, evidence_kind=curated|structured_metadata,
  optional evidence_code, evidence_text, source_url, imported_at
POST /api/v1/ontology/{kind}/{id}/parents
  parent_id, source, source_identifier, source_release, optional source/evidence metadata
```

Duplicates return `409`, missing/wrong-aspect targets `404`, unsupported or malformed payloads `422`, and concurrent hierarchy validation may return retryable `409`. New writes return `503` when the administrator token is unconfigured and `401` for missing/incorrect credentials. These create-only interfaces do not implement source-history reconciliation or editing/deprecation yet. No enrichment operation is exposed.

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
GET   /api/v1/graph/{gene|protein|variant|disease|publication}/{id}
GET   /api/v1/graph/gene/by-symbol/{symbol}?taxonomy_id=9606
POST  /api/v1/relationships/gene-disease
POST  /api/v1/relationships/variant-gene
POST  /api/v1/relationships/variant-disease
POST  /api/v1/relationships/protein-interaction
```

Phase 7 adds `GET /api/v1/pathways`, `GET /api/v1/pathways/{id}`, `GET /api/v1/ontology/{biological_process|molecular_function}`, and `GET /api/v1/ontology/{kind}/{id}` plus the protected POST routes described above. New collections accept `q` (literal partial name/identifier matching, at most 200 characters), `page` and `page_size` (1–100). Graph/relationship root type parameters also accept `pathway`, `biological_process`, and `molecular_function`. New relationship filters are `gene_pathway`, `gene_biological_process`, `protein_molecular_function`, `biological_process_parent`, and `molecular_function_parent`. Unified search remains limited to its previous four categories; use functional collection filtering for new types.

Collection endpoints accept one-based `page` and bounded `page_size` parameters. The response includes `items`, `page`, `page_size`, `total`, and `pages`.

Graph reads accept `depth`, `max_nodes`, `max_edges`, repeated `type=gene|protein|disease|variant|publication`, and repeated `relationship_type` parameters. The kinds are `gene_protein`, `gene_disease`, `variant_gene`, `variant_disease`, `protein_interaction`, `publication_gene`, `publication_protein`, and `publication_disease`. Numeric roots use positive internal IDs, not external identifiers. `/api/graph/gene/{symbol}` is a compatibility alias; versioned routes are canonical. Graph responses use `root_id`, `nodes`, `edges`, `limits`, `truncated`, `truncation_reasons`, and `scanned_edges` rather than collection pagination.

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

### Phase 6 verification and change record (2026-10-23)

- 48 backend tests passed with an isolated PostgreSQL 17 instance, including actual slow-query cancellation, transaction-local timeout reset, bounded graph traversal, all root types, cycles, parallel edges, filters, provenance and prior-phase regressions.
- 25 frontend tests passed, including bounded workspace merging, shared-branch collapse, source inspection, expansion/retry, empty/partial states, shareable query controls and request cancellation. The canvas is mocked in unit tests; browser rendering is verified separately.
- Ruff lint/format, strict mypy, ESLint, Prettier, TypeScript and the production Vite build passed. Cytoscape is in a separate lazy-loaded graph chunk (~143 kB gzipped).
- All five existing migrations applied on a fresh isolated PostgreSQL 17 database, with no schema differences. No Phase 6 schema migration was required.
- Docker images built successfully. Updating an existing frontend dependency volume exposed pnpm's non-interactive purge prompt; the Compose frontend now sets `CI=true` so locked dependency refreshes can proceed without a TTY and without deleting PostgreSQL data.
- Live Docker HTTP checks passed for API version 0.6.0, graph lookup and node-cap warnings, previous search, and publication browsing. The alternate-port verification stack used frontend 5175/API 8005 because default ports were occupied. Manual browser verification confirmed actual canvas rendering, edge-source inspection, keyboard node selection, collapse/re-expansion, zoom and fit on the explicitly labeled demo neighborhood.
- The upstream Starlette/AnyIO deprecation warning remains; a local pytest cache-permission warning does not affect test execution. Graph performance on production-scale biological datasets remains unbenchmarked.

Important Phase 6 files: `backend/app/schemas/graph.py`, `repositories/graph.py`, `services/graph.py`, `api/v1/graph.py`, `services/relationships.py`, graph unit/PostgreSQL tests, `frontend/src/features/graph/`, `pages/GraphPage.tsx`, `test/Phase6.test.tsx`, graph entry links, and Compose/configuration updates.

### Phase 7 verification and change record (2026-10-23)

- 57 backend tests passed, including all previous phases, direct functional annotations, GO identity/aspects, multi-parent DAG and cycle rejection, literal filtering, authorization, SQL-level namespace/self-edge constraints, and a real PostgreSQL concurrent hierarchy-lock check.
- 30 frontend tests passed, including live-record home preview/loading/empty/error/retry behavior, functional collection filters/navigation, source-release detail display and graph links. Ruff lint/format, strict mypy, ESLint, Prettier, TypeScript and the production build passed.
- Six migrations applied successfully on a clean isolated PostgreSQL 17 database; Alembic reports no pending schema differences. The historical publication runtime test now compares the database revision to the current Alembic head instead of a hardcoded Phase 5 revision.
- API-contract graph tests use an injected deterministic clock so background desktop/build load does not change assertion equivalence. Separate cooperative budget tests and actual PostgreSQL query-cancellation tests retain real timeout coverage.
- The existing Docker development stack upgraded to 0.7.0 without deleting data. Live HTTP checks confirmed graph regression, new empty functional collections and API version. Browser checks confirmed the redesigned home panel with a real local demo record, source labeling, and functional collection navigation/empty states. The panel was also checked at a 430-pixel viewport and the default viewport restored afterward.
- Local pnpm cache files are excluded from Docker context, ESLint and Prettier. They are build/dependency artifacts, not project source. The upstream AnyIO deprecation and local pytest cache-permission warnings remain non-fatal.

Important Phase 7 files: `backend/app/models/ontology.py`, `schemas/ontology.py`, `repositories/ontology.py`, `services/ontology.py`, `services/ontology_relationships.py`, `api/v1/ontology.py`, migration `20261023_0006_ontology.py`, ontology unit/PostgreSQL tests, the existing relationship/graph extensions, frontend functional collection/detail pages and configuration, `ResearchEntryPanel.tsx`, `HomePage.tsx`, styles and `Phase7.test.tsx`.

## Product principles

- Never fabricate scientific data. Development fixtures are visibly labeled.
- Preserve provenance so imported information can be traced to a provider and source identifier.
- Keep provider response formats behind adapters and normalization boundaries.
- Prefer a modular monolith until operational evidence justifies more infrastructure.
- Paginate and filter in the database rather than loading entire collections into memory.
- Treat migrations, tests, documentation, and observable failures as part of the product.
- Add complexity only when it supports a working phase.

## Known limitations

- Graph safety limits intentionally omit oversized neighborhoods; there are no complete degree counts, relevance-ranked graph sampling, saved layouts, export, or production-scale graph benchmarks yet. Workspace expansions/layout are not persisted in shareable URLs. Graph traversal covers eight entity types, not organisms or future dataset entities.
- Functional records and direct assertions are source-backed administrator entries, not automatic GO/Reactome imports. There is no ontology release archive, obsolete-term handling, negative annotation support, evidence-code registry validation, ancestor annotation propagation, or statistical enrichment. A syntactically valid GO ID is not proof of correct aspect or biological content.
- Ontology cycle checks use a service-level lock and bounded recursive query, not a universal SQL DAG constraint. Direct SQL writes must honor that service boundary. Functional collections use bounded offset pagination and synchronous counts; large-scale hierarchy and membership performance is unbenchmarked.
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

Phase 8 will add justified background processing, tracked import jobs, retries and bounded batch workflows. It has not been started. A statistical enrichment engine remains a separate future extension requiring an explicit background population and reproducible method.

Enrichment calculations, OpenSearch/Elasticsearch, background processing, and later-phase infrastructure remain out of scope for Phase 7.

## Contributing

1. Keep changes within the active phase.
2. Include tests for behavior changes.
3. Add migrations for schema changes; never rewrite applied migration history.
4. Keep external payloads outside domain and persistence interfaces.
5. Maintain current behavior, architecture, and verification records in `README.md`; historical architecture/changelog files are retained. Local roadmap, prompt, and report Markdown files are not release artifacts and are not included in commits.

## License

A license has not yet been selected. The project intends to be open source, but distribution and reuse terms are not established until a `LICENSE` file is added.
