import { useSearchParams } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { GraphWorkspace } from "../features/graph/GraphWorkspace";
import { graphParams } from "../features/graph/state";
import { entityTypes, relationshipLabels } from "../features/graph/types";
import type { GraphLimits, RelationshipType } from "../features/graph/types";
import type { RelatedEntityType } from "../types/entities";

function bounded(value: string | null, fallback: number, max: number) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 1 && parsed <= max ? parsed : fallback;
}

export function GraphPage() {
  const [params, setParams] = useSearchParams();
  const type = entityTypes.includes(params.get("type") as RelatedEntityType)
    ? (params.get("type") as RelatedEntityType)
    : "gene";
  const id = params.get("id");
  const symbol = params.get("symbol");
  const limits: GraphLimits = {
    depth: bounded(params.get("depth"), 1, 3),
    max_nodes: bounded(params.get("max_nodes"), 60, 150),
    max_edges: bounded(params.get("max_edges"), 120, 300),
    entity_types: params
      .getAll("node_type")
      .filter((value): value is RelatedEntityType =>
        entityTypes.includes(value as RelatedEntityType),
      ),
    relationship_types: params
      .getAll("relationship_type")
      .filter((value): value is RelationshipType => Object.hasOwn(relationshipLabels, value)),
  };
  const apiParams = graphParams(limits);
  apiParams.set("taxonomy_id", params.get("taxonomy_id") ?? "9606");
  const resource =
    id && /^[1-9]\d*$/.test(id)
      ? `graph/${type}/${id}?${apiParams}`
      : symbol
        ? `graph/gene/by-symbol/${encodeURIComponent(symbol)}?${apiParams}`
        : null;

  function update(values: Record<string, string>) {
    const next = new URLSearchParams(params);
    Object.entries(values).forEach(([key, value]) =>
      value ? next.set(key, value) : next.delete(key),
    );
    setParams(next);
  }

  function toggleFilter(key: string, value: string, all: string[]) {
    const selected = params.getAll(key);
    const current = selected.length ? selected : all;
    const nextValues = current.includes(value)
      ? current.filter((item) => item !== value)
      : [...current, value];
    if (!nextValues.length) return;
    const next = new URLSearchParams(params);
    next.delete(key);
    nextValues.forEach((item) => next.append(key, item));
    setParams(next);
  }

  return (
    <div className="page-container graph-page">
      <PageHeader
        eyebrow="Knowledge graph"
        title="Explore connected evidence"
        description="Navigate stored biological relationships and inspect the source behind each connection."
        showSearch={false}
      />
      <form
        className="graph-root-form"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const value = String(form.get("symbol") ?? "").trim();
          if (value)
            setParams({
              symbol: value,
              taxonomy_id: String(form.get("taxonomy_id") ?? "9606"),
              depth: String(limits.depth),
            });
        }}
      >
        <label>
          Gene symbol
          <input
            name="symbol"
            aria-label="Gene symbol"
            key={symbol ?? ""}
            defaultValue={symbol ?? ""}
            placeholder="TP53"
            required
            maxLength={64}
          />
        </label>
        <label>
          Taxonomy ID
          <input
            name="taxonomy_id"
            aria-label="Taxonomy ID"
            key={params.get("taxonomy_id") ?? "9606"}
            defaultValue={params.get("taxonomy_id") ?? "9606"}
            required
            maxLength={32}
          />
        </label>
        <button className="button" type="submit">
          Explore gene
        </button>
      </form>
      <div className="graph-query-controls">
        <label>
          Initial depth
          <select value={limits.depth} onChange={(event) => update({ depth: event.target.value })}>
            {[1, 2, 3].map((value) => (
              <option key={value} value={value}>
                {value} hop{value > 1 ? "s" : ""}
              </option>
            ))}
          </select>
        </label>
        <label>
          Node limit
          <select
            value={limits.max_nodes}
            onChange={(event) => update({ max_nodes: event.target.value })}
          >
            {[...new Set([30, 60, 100, 150, limits.max_nodes])]
              .sort((a, b) => a - b)
              .map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
          </select>
        </label>
        <label>
          Relationship limit
          <select
            value={limits.max_edges}
            onChange={(event) => update({ max_edges: event.target.value })}
          >
            {[...new Set([60, 120, 200, 300, limits.max_edges])]
              .sort((a, b) => a - b)
              .map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
          </select>
        </label>
      </div>
      <details className="graph-filters">
        <summary>Filter node and relationship types</summary>
        <fieldset>
          <legend>Node types</legend>
          {entityTypes.map((value) => (
            <label key={value}>
              <input
                type="checkbox"
                checked={
                  value === (symbol && !id ? "gene" : type) ||
                  !limits.entity_types.length ||
                  limits.entity_types.includes(value)
                }
                disabled={value === (symbol && !id ? "gene" : type)}
                onChange={() => toggleFilter("node_type", value, entityTypes)}
              />
              <span className={`graph-type graph-type--${value}`}>{value}</span>
            </label>
          ))}
        </fieldset>
        <fieldset>
          <legend>Relationship types</legend>
          {Object.entries(relationshipLabels).map(([value, label]) => (
            <label key={value}>
              <input
                type="checkbox"
                checked={
                  !limits.relationship_types.length ||
                  limits.relationship_types.includes(value as RelationshipType)
                }
                onChange={() =>
                  toggleFilter("relationship_type", value, Object.keys(relationshipLabels))
                }
              />
              {label}
            </label>
          ))}
        </fieldset>
      </details>
      {resource ? (
        <GraphWorkspace key={resource} resource={resource} />
      ) : (
        <p className="graph-intro">
          Start with a gene symbol, or choose “Explore graph” on an entity page, including a pathway
          or GO term. No relationships are inferred from a matching name.
        </p>
      )}
    </div>
  );
}
