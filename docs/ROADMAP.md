# Long-term roadmap and implementation coverage

This is a concise reference to the 0–50 roadmap supplied by the project owner.
It preserves its phase names and direction; it is not a verbatim copy of the full
owner document or an instruction to implement every phase immediately.

**Roadmap phases and historical BKP implementation milestones use different
numbering.** The historical “Phase 8” release 0.8.0 delivered tracked imports.
It did not complete long-term roadmap phases 0–8. Releases 0.9–0.11 address a
bounded part of long-term **Phase 2**, not long-term Phase 9.

## Direction

Database → biological knowledge base → search → knowledge graph →
bioinformatics analysis → scientific intelligence → AI-assisted research.
Correctness, useful biology, provenance, reproducibility and justified complexity
take priority over code volume or premature infrastructure.

## Coverage updated through 0.23.0

| Roadmap phase | Long-term scope | Current coverage / remaining work |
|---|---|---|
| 0 | Architectural Foundation | Implemented layered FastAPI/PostgreSQL/React foundation; evolves with later work. |
| 1 | Core Application Platform | Running application, entity APIs, migrations, tests and Compose. |
| 2 | Biological Data Model | Partial: organisms, genes, proteins, external IDs, source-backed gene aliases and reference sequence placements and sourced transcripts. Normalized chromosomes/assemblies and broader identifier namespaces remain; a sourced NCBI/Ensembl registry is implemented. |
| 3 | External Data Integration Framework | Partial: NCBI Gene, UniProt, PubMed adapters, bounded retries, normalization, request pacing. A bounded Ensembl transcript adapter now exists; no general bulk source-version/pagination framework. |
| 4 | Data Ingestion Engine | Partial: idempotent single-record and bounded queued imports, record status/results and crash replay. No large-scale incremental source synchronization or full checkpoint framework. |
| 5 | Provenance and Data Quality System | Partial: record/assertion provenance, identity and namespace constraints, safe errors. Initial bounded metadata/consistency/refresh dashboard for genes/proteins/transcripts/identifiers; no comprehensive quality coverage, immutable payload/source snapshots or claim history. |
| 6 | Unified Search | Partial: PostgreSQL ranking, filters, suggestions, gene aliases and thirteen stored entity categories, including phenotypes, transcripts, diseases, variants, pathways and three GO kinds. Future entity coverage and fuzzy/synonym expansion remain. |
| 7 | Diseases and Phenotypes | Partial: diseases and explicit gene/variant disease assertions. Sourced phenotype terms and qualified disease annotations are implemented; automatic HPO ingestion, disease ontology term modeling and broader phenotype annotation scope remain. |
| 8 | Genetic Variants | Partial: basic variants and gene/disease assertions. Sourced assembly-aware literal placements and parent identity/taxonomy guards are implemented. Clinical significance/frequency, protein/publication links, reference validation and biological normalization remain absent. |
| 9 | Pathways and Biological Ontologies | Partial: pathways, GO biological process/molecular function and sourced direct annotations/is_a. Cellular components, sourced direct protein annotations and same-aspect hierarchy/graph/search are supported; automatic ontology ingestion and enrichment remain absent. |
| 10 | Publication and Literature System | Partial: PubMed metadata and explicit gene/protein/disease links. Source-supplied keywords and variant literature links are implemented. No full-text corpus or drug links; exact dataset citation links now exist, but no NLP extraction or complete source snapshot history. |
| 11 | Dataset Discovery | Initial GEO Series metadata model, catalogue, detail, source references and bounded explicit import. Additional repositories, source-backed tissue/disease annotations, broader discovery remain. Exact source-reported local publication links are supported. |
| 12 | Knowledge Graph Core | Partial: bounded projections over existing typed relations, now including first observed GEO dataset citation links. No general coverage of all future node/edge kinds. |
| 13 | Interactive Knowledge Graph Explorer | Implemented for currently supported nodes/relations; visible JSON/GraphML view exports preserve source evidence and partial-view context. Production-scale performance and additional entity types remain. |
| 14 | Advanced Data Engineering Infrastructure | Partial: durable PostgreSQL singleton worker, retries, queued GEO metadata and public aggregate monitoring; detailed jobs remain protected. No scheduling, distributed workers, Redis/Celery or large-scale processing. |
| 15 | Advanced Search Infrastructure | Initial opt-in PostgreSQL indexed name hints; no separate search engine/index, scale infrastructure or semantic retrieval. |
| 16 | Bioinformatics Analysis Engine | Initial exact local gene-list overlap with coverage, set counts and descriptive Jaccard index. Enrichment/statistical testing remain absent. |
| 17 | Genomics Toolkit | Not implemented; placement metadata is a prerequisite, not a genome browser or file-analysis toolkit. |
| 18 | Transcriptomics | Not implemented. |
| 19 | Proteomics and Protein Interactions | Partial: proteins and sourced protein interactions. Abundance, families, domains and PTMs absent. |
| 20 | Structural Biology | Not implemented. |
| 21 | Drugs and Pharmacology | Not implemented. |
| 22 | Clinical Trials | Not implemented. |
| 23 | Researcher and Institution Network | Not implemented; publication authors are text, not resolved researcher identities. |
| 24 | Scientific Trend Analytics | Not implemented. |
| 25 | Research Dashboard | Not implemented; the live-record home panel is not an analytics dashboard. |
| 26 | User Accounts and Personal Workspace | Not implemented; a server admin bearer token is not a user-account system. |
| 27 | Alerts and Research Monitoring | Not implemented. |
| 28 | Programmatic API | Partial: versioned REST API and local CLI. No public SDK/R package or full programmatic product. |
| 29 | Export and Interoperability | Partial JSON API and visible graph JSON/GraphML downloads; no general bulk export subsystem. |
| 30 | Workflow and Analysis System | Not implemented. |
| 31 | Reproducible Research | Partial source context only; no reproducible analysis runs or complete source snapshots. |
| 32 | Machine Learning Foundation | Not implemented. |
| 33 | NLP for Scientific Literature | Not implemented; no machine-extracted biological claims. |
| 34 | Semantic Search | Not implemented. |
| 35 | RAG Knowledge System | Not implemented. |
| 36 | AI Research Assistant | Not implemented. |
| 37 | Hypothesis Generation | Not implemented. |
| 38 | Graph Analytics | Not implemented; bounded neighborhood traversal is not statistical network analysis. |
| 39 | Multi-omics Integration | Not implemented. |
| 40 | Advanced Visual Analytics | Partial graph navigation only; no dedicated scientific plotting subsystem. |
| 41 | Collaborative Research | Not implemented. |
| 42 | Plugin / Extension System | Not implemented. |
| 43 | Large-scale Distributed Data Processing | Not implemented; introduce only when measured workloads justify it. |
| 44 | High Performance Bioinformatics | Not implemented. |
| 45 | Data Versioning | Partial migration/retrieval metadata only; no biological source version archive. |
| 46 | Full Observability | Partial logs, request IDs, healthchecks and job status. No full metrics/tracing/alerting. |
| 47 | Security and Access Control | Partial protected newer writes and read-only public proxy. No general RBAC/account system. Basic security is required now, not deferred until this phase. |
| 48 | Production Infrastructure | Partial CI, isolated temporary public student preview, backup/restore checks and rollback images. Long-term hosting, off-site backups and disaster recovery remain. |
| 49 | Public Open-source Platform | Partial public repository/docs/CI/PR workflow. No selected open-source license or complete contributor ecosystem. |
| 50 | Mature Bioinformatics Research Platform | Long-term target, not a delivered feature. |

## Current increment and next candidates

Release 0.11.0 extends sourced transcripts with a namespaced NCBI/Ensembl
identifier registry, explicit UniProt mapping evidence and live-compatible Ensembl
metadata handling. See [transcripts](TRANSCRIPTS.md) and the earlier
[gene context](GENE_CONTEXT.md). These increments advance long-term Phases 2–3.

Remaining Phase 2 candidates include broader identifier namespaces and
normalized assembly/chromosome models. Transcript exon/translation models and
large-scale refresh require their own source/identity contracts.
Later dataset/phenotype/enrichment features must state their own source and
reproducibility requirements before implementation.

A phase proceeds only when its prerequisites work, it adds actual value,
complexity is justified and existing stability/provenance are preserved.

## Release 0.11 follow-up

The sourced NCBI/Ensembl identity registry and explicit provider cross-references
advance parts of long-term Phases 2–3. This does not complete either phase or the
subsequent dataset-discovery phase. See [identifier operations](GENE_IDENTIFIERS.md).

## Release 0.12 follow-up

An initial Phase 5 quality/provenance review adds ten read-only checks over the
existing gene/protein/transcript/identifier data. It does not complete Phase 5 or
certify biological correctness. Broader metadata normalization and provider/source
versioning remain prerequisites for later whole-platform quality workflows.
See [data quality](DATA_QUALITY.md).

## Release 0.13 follow-up

Long-term Phase 6 now searches ten stored categories with counts, filters and
suggestions. This adds navigation to existing data rather than importing new facts.
Fuzzy/semantic search, ontology-synonym expansion and future entity types remain.
See [unified search](UNIFIED_SEARCH.md).

## Release 0.14 follow-up

Phase 7 gains sourced HPO-identified terms and explicit present/excluded disease
annotations, both read directions, public browsing and unified search. The catalogue
starts empty; this is not completion of Phase 7 or an HPO import engine.
See [phenotypes](PHENOTYPES.md).

## Release 0.15 follow-up

Phase 8 gains explicit assembly/sequence/coordinate/allele source observations for
existing variants. This is not a VCF importer, full variant normalization or clinical
annotation engine. New placement collections start empty.
See [variant placements](VARIANT_PLACEMENTS.md).

## Release 0.16 follow-up

Phase 9 now includes GO cellular components with direct sourced protein annotations,
same-aspect hierarchy, unified search and bounded graph navigation. No annotation
propagation, ontology import or enrichment is implied; this is not completion of
the phase. See [cellular components](CELLULAR_COMPONENTS.md).

## Release 0.17 follow-up

Phase 10 adds bounded PubMed keyword metadata and explicit variant literature
references through existing search, detail, relationships and graph. Bounded
real PubMed imports are tested on a restored database before public loading.
See [literature metadata](LITERATURE_METADATA.md).

## Release 0.18 follow-up

Phase 11 begins with public GEO Series metadata discovery, explicit bounded import,
source access and unified search. No experimental files or sample-level/clinical
analyses are fetched or inferred. Other repositories and graph integration remain.
See [datasets](DATASETS.md).

## Release 0.19.0 — bounded Phase 12 follow-up

Datasets enter the existing knowledge graph through source-reported publication
citations resolved by exact local PMID. First observed evidence is retained across
metadata refresh; catalogue detail and graph allow navigation in both directions.
This does not complete Phase 12 or add inferred gene/disease/organism edges, graph
analytics, scheduling or a general graph storage engine. See DATASET_GRAPH.md.

## Release 0.20.0 — Phase 13 explorer follow-up

The visible graph can be downloaded as JSON/GraphML with provenance, traversal
limits and partial-view notes. This also advances a small part of Phase 29,
without implementing general exports or reproducible analysis history.
See GRAPH_EXPORT.md.

## Release 0.21.0 — Phase 14 follow-up

GEO Series metadata now uses existing durable jobs with cancellation, retry and
idempotent replay. Read-only aggregate monitoring is exposed in the retained new
frontend. No heartbeat, scheduler or distributed processing is introduced.
See DATASET_IMPORT_JOBS.md.

## Release 0.22.0 — initial Phase 15 follow-up

Opt-in lexical name hints use existing PostgreSQL trigram indexes and keep
ordinary search and identifier matching unchanged. A separate search cluster
remains unjustified for the current small catalogue. See NAME_HINTS.md.

## Release 0.23.0 — Phase 16 foundation

A bounded read-only comparison resolves gene lists exactly within one organism
and reports intersection, unique sets and Jaccard over resolved records. Unknowns,
method version and current provenance are explicit. No enrichment or p-values are
fabricated from the small catalogue. See GENE_OVERLAP.md.
