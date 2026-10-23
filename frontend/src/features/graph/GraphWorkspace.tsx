import { useState } from "react";
import { Link } from "react-router-dom";

import { ProvenanceBadge } from "../../components/ProvenanceBadge";
import { ErrorState, LoadingState } from "../../components/States";
import { GraphCanvas } from "./GraphCanvas";
import { entityTypes, truncationLabels } from "./types";
import type { GraphSelection } from "./types";
import { useGraphExplorer } from "./useGraphExplorer";

export function GraphWorkspace({ resource }: { resource: string }) {
  const { graph, loading, error, retry, expand, collapse, expanding, expansionError } =
    useGraphExplorer(resource);
  const [selected, setSelected] = useState<GraphSelection | null>(null);
  if (loading) return <LoadingState label="Loading sourced graph" />;
  if (error) return <ErrorState message={error} onRetry={retry} />;
  if (!graph) return null;
  const node =
    selected?.kind === "edge"
      ? null
      : (graph.nodes.find((item) => item.id === (selected?.id ?? graph.root_id)) ?? graph.nodes[0]);
  const edge =
    selected?.kind === "edge" ? graph.edges.find((item) => item.id === selected.id) : null;
  const activeSelection = edge ? selected : node ? { kind: "node" as const, id: node.id } : null;
  return (
    <section className="graph-workspace" aria-label="Knowledge graph workspace">
      <div className="graph-summary" aria-live="polite">
        <strong>
          {graph.nodes.length} nodes · {graph.edges.length} relationships
        </strong>
        <button type="button" onClick={retry} disabled={!!expanding}>
          Reset view
        </button>
      </div>
      <div className="graph-legend" aria-label="Graph node type legend">
        {entityTypes.map((type) => (
          <span key={type} className={`graph-type graph-type--${type}`}>
            {type}
          </span>
        ))}
      </div>
      {graph.truncated && (
        <div className="graph-limit-notice" role="status">
          Partial graph:{" "}
          {graph.truncation_reasons.map((reason) => truncationLabels[reason]).join("; ")}. Try a
          smaller depth or narrower filters.
        </div>
      )}
      {graph.edges.length === 0 && (
        <p className="context-note">
          No stored relationships match this view. This does not establish the absence of biological
          connections.
        </p>
      )}
      <div className="graph-layout">
        <GraphCanvas graph={graph} selected={activeSelection} onSelect={setSelected} />
        <aside className="graph-inspector" aria-label="Graph inspection">
          <h2>Inspect the evidence</h2>
          <label>
            Inspect node
            <select
              value={node?.id ?? ""}
              onChange={(event) => setSelected({ kind: "node", id: event.target.value })}
            >
              {!node && <option value="">Select a node</option>}
              {graph.nodes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.entity_type}: {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Inspect relationship
            <select
              value={edge?.id ?? ""}
              onChange={(event) => {
                if (event.target.value) setSelected({ kind: "edge", id: event.target.value });
              }}
            >
              <option value="">Select a relationship</option>
              {graph.edges.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.assertion.subject.label} → {item.assertion.predicate} →{" "}
                  {item.assertion.object.label} · {item.assertion.source} (
                  {item.assertion.source_identifier ?? item.id})
                </option>
              ))}
            </select>
          </label>
          {node && (
            <div className="graph-node-details">
              <span className={`graph-type graph-type--${node.entity_type}`}>
                {node.entity_type}
              </span>
              <h3>{node.label}</h3>
              <Link to={node.href}>Open entity page ↗</Link>
              <div className="graph-node-actions">
                <button type="button" disabled={!!expanding} onClick={() => void expand(node)}>
                  {expanding === node.id ? "Expanding…" : "Expand node"}
                </button>
                <button type="button" disabled={!!expanding} onClick={() => collapse(node.id)}>
                  Collapse branch
                </button>
              </div>
              <p className="context-note">
                Collapse hides nodes reached only through this branch. Nodes shared with another
                path remain visible.
              </p>
            </div>
          )}
          {edge && (
            <div className="graph-edge-details">
              <h3>{edge.assertion.predicate.replaceAll("_", " ")}</h3>
              <p>
                <Link to={edge.assertion.subject.href}>{edge.assertion.subject.label}</Link>{" "}
                {edge.directed ? "→" : "↔"}{" "}
                <Link to={edge.assertion.object.href}>{edge.assertion.object.label}</Link>
              </p>
              <ProvenanceBadge source={edge.assertion.source} />
              <dl>
                <dt>Source identifier</dt>
                <dd>{edge.assertion.source_identifier ?? "Not supplied"}</dd>
                <dt>Provenance basis</dt>
                <dd>
                  {edge.assertion.provenance_basis === "protein_record"
                    ? "Inherited from protein record"
                    : "Relationship assertion"}
                </dd>
                <dt>Acquisition</dt>
                <dd>{edge.assertion.evidence_kind?.replaceAll("_", " ") ?? "Not classified"}</dd>
                <dt>Retrieved</dt>
                <dd>{edge.assertion.imported_at ?? "Not supplied"}</dd>
              </dl>
              {edge.assertion.evidence_text && <p>{edge.assertion.evidence_text}</p>}
              {edge.assertion.source_url && (
                <a href={edge.assertion.source_url} target="_blank" rel="noreferrer">
                  Open relationship source ↗
                </a>
              )}
            </div>
          )}
          {expansionError && (
            <div role="alert">
              <p>{expansionError}</p>
              <p>The existing graph is preserved. Use Expand node to retry.</p>
            </div>
          )}
          <p className="context-note">
            A literature mention or sourced association is not proof of causation. This graph
            reflects only the local database.
          </p>
        </aside>
      </div>
    </section>
  );
}
