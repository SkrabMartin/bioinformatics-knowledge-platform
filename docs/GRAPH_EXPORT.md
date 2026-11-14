# Visible graph export — release 0.20.0

The Phase 13 explorer now downloads its current visible view as JSON or GraphML.
This also starts a bounded part of Phase 29 interoperability; it does not complete
either phase or add a general database export/API endpoint.

## Scope and scientific meaning

Export includes only the currently visible nodes and edges. Expanded nodes are
included; collapsed branches are excluded. Source assertions remain unchanged,
including source identifiers/URLs, evidence, retrieval time, source record date,
qualifiers and timestamps where the API supplies them. Parallel assertions and
undirected/self edges are preserved as separate edges.

`truncated`, `truncation_reasons`, traversal limits and scanned-edge count remain
in the export even after collapse. A view without server truncation is still not
a complete database or biological network. Missing links do not establish absence
of biological relationships. Source associations do not establish causation;
dataset citations may be first observed references no longer listed by the source.

## JSON contract

The UTF-8 file uses envelope `format: bkp.graph-view.v1`, application version,
`exported_at`, `scope: visible_graph`, `initial_request`, explanatory `notes` and
`graph` containing the visible GraphResponse. Browser export time is separate
from source retrieval time. Navigation hrefs are relative BKP paths.

Nodes and edges are sorted by typed IDs without modifying the displayed state.
The initial API resource identifies the original request and filters; subsequent
expansion/collapse are not reconstructed from it. Depth values are inherited from
constituent requests, not recomputed shortest paths. Candidate counts can repeat
across expansions. There is no query history, guaranteed replay, cross-request
transaction snapshot, complete data version or saved analysis run.

## GraphML contract

The exporter uses the [GraphML key/data model and edge direction semantics](https://graphml.graphdrawing.org/primer/graphml-primer.html).
Namespaced XML is constructed through DOM text nodes rather than concatenating
provider text into markup. Local XML IDs `n0` / `e0` avoid restrictions on typed
BKP identifiers. `node_json` retains the complete original node/typed ID;
`assertion_json` retains the complete source assertion; `bkp_edge_id` retains the
original edge ID. Graph-level `metadata_json` contains the envelope and view
root/limits/truncation/candidate counts. Labels, entity type, predicate and source
also have plain string fields for graph tools. Direction is set per edge.

Tools differ in support for mixed directed/undirected graphs and JSON-valued
attributes; no universal importer compatibility is promised. Layout, selection,
canvas zoom, styling and collapse history are not exported. The format is not an
SVG/PNG image. Text that XML 1.0 cannot represent causes a visible error and JSON
remains available, rather than silently discarding evidence.

## Operation and verification

Downloads are created locally in the browser from already loaded data. They do
not call another service, import records or write to the server. Both buttons are
disabled while expansion is pending. Failure preserves the view and is announced
as an accessible error. Temporary download URLs are released after a short delay.

No database migration, schema change, new package or new write permission is
needed. Existing backups and rollback images are retained before deployment.
Tests cover evidence/Unicode/XML round trips, partial/collapsed scope, endpoint
integrity, mixed direction/self edges, JSON fallback, URL cleanup and UI failures.
