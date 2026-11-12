# Cellular components — 0.16.0

This increment advances long-term Phase 9 by adding the previously missing GO
cellular-component aspect to the existing functional knowledge framework. GO
organizes terms into molecular function, biological process and cellular component;
see the [official GO overview](https://www.geneontology.org/docs/ontology-documentation/).
BKP now represents all three aspects, but does not implement the entire GO model.

## Stored terms and assertions

`cellular_component` terms use the shared `ontology_terms` identity, GO ID, name,
optional description and source-release metadata. GO IDs remain globally unique
across the three kinds. A syntactically valid ID does not establish that a submitted
term exists or has the correct aspect/name in a live GO release: administrators
must supply accurate source-backed records.

`ProteinCellularComponent` stores a direct protein-to-term assertion, source record,
release, evidence kind/code and optional source URL, retrieval time and evidence
text, following the existing BP/MF annotation contract. The unique source assertion
key is protein, term, source and source identifier. Duplicate creation returns 409;
this release does not provide immutable source-release snapshots or annotation edits.

The relationship predicate is `annotated_to`, an application-level assertion link.
It does not substitute for every formal GO/RO relation or claim continuous cellular
localization in every context. Only directly supplied positive annotations are
supported. `qualifier: NOT` and other unknown annotation fields are rejected rather
than silently dropped. Negative assertions, GO extensions and complete GO annotation
file semantics require further modeling before an importer can use them.

The schema ties annotation `term_id` and `kind` to a shared term's matching composite
identity and fixes the annotation kind to cellular component. Cross-aspect targets
fail at both service and database layers. No protein annotations are inferred from
text, protein names, absence of data or a hierarchy traversal.

## API, hierarchy and graph

Existing generic routes now accept `cellular_component`:

- `GET /api/v1/ontology/cellular_component` with existing bounded pagination and
  name/GO ID filtering; detail at `/{id}`.
- Protected `POST /api/v1/ontology` accepts the new kind with source metadata.
- Protected `POST /api/v1/ontology/cellular_component/{id}/annotations` uses a protein
  `entity_id` and explicit evidence/source fields.
- Protected `POST /api/v1/ontology/cellular_component/{id}/parents` uses the existing
  parent-creation contract for direct `is_a` assertions.
- `GET /api/v1/relationships/cellular_component/{id}` and the protein relationship
  view expose direct assertions and their evidence in both directions.
- `GET /api/v1/graph/cellular_component/{id}` and existing protein-rooted graphs
  traverse stored annotations/parents with the existing budgets and filters.

Same-aspect composite foreign keys and the existing bounded cycle/ancestor checks
apply to CC hierarchies too. Multiple parents can be stored. An `is_a` path is not
an automatically materialized annotation to every ancestor. Other ontology relations,
annotation propagation, enrichment and source ingestion are not added.

The graph adds `protein_cellular_component` and `cellular_component_parent` edge
types plus cellular-component nodes. Public mutation methods remain blocked by the
existing proxy; new administrative operations retain fail-closed token protection.

## Interface and search

`/cellular-components` and `/cellular-component/{id}` reuse the functional catalogue
and detail views, including source release, provenance, direct relationships and
graph links. The functional collection navigation exposes the new category. Graph
filters and rendering recognize the new node/edge types. Unified search and
suggestions now support twelve categories, including CC GO ID/name/description
matching and detail links. Clients with closed enums must add these types or keep
explicit existing filters. Older search responses lacking CC counts render as zero.

The new catalogue starts empty. No real or synthetic CC term, annotation or parent
is automatically imported during deployment. Existing BP/MF data and API contracts
remain supported. Existing quality-review scope remains unchanged.

## Migration and rollback

Migration `20261112_0013` widens the allowed kind checks in `ontology_terms` and
`ontology_parents` without altering existing rows. It creates
`protein_cellular_components`, source/target indexes, composite restrictive foreign
keys, kind/evidence checks and source-assertion uniqueness. Fresh migrations and
upgrading a restored live backup must both pass model comparison and tests.

Before rollout, retain previous backend/frontend images and a privately restored,
checksum-verified live backup. Verify existing record/ontology counts after upgrade,
then check the previous application against the upgraded clone. Rollback retains
the new migration service and expanded schema while reverting application images;
older migration images cannot recognize the new revision. The downgrade refuses
when CC terms or annotations exist instead of deleting their data. No live downgrade,
reset or volume deletion is part of deployment.

Release validation passed 202 backend and 50 frontend tests with migration/model,
lint, formatting, typing and build checks. PostgreSQL tests exercised kind-separated
search, direct evidence serialization, graph traversal, cross-aspect rejection,
cycles and duplicate source assertions. The restored starter backup retained its
three genes, three proteins, 128 transcripts and six evidenced gene identities.
Ontology counts were unchanged and CC remained empty. The previous 0.15 backend
successfully read the upgraded clone.

The deployed 0.16 instance passed public HTTPS checks for CC catalogue/search,
relationship/graph route validation, the existing protein graph, original catalogue
totals and the new SPA bundle. Public writes remained blocked. Migration head is
20261112_0013; both the CC term catalogue and protein annotation table remain empty.
