import { version } from "../../../package.json";
import type { GraphResponse } from "./types";

export interface GraphExport {
  format: "bkp.graph-view.v1";
  app_version: string;
  exported_at: string;
  scope: "visible_graph";
  initial_request: string;
  notes: string[];
  graph: GraphResponse;
}

export function captureGraph(
  graph: GraphResponse,
  resource: string,
  now = new Date(),
): GraphExport {
  const copy = structuredClone(graph);
  const compare = (a: { id: string }, b: { id: string }) =>
    a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  copy.nodes.sort(compare);
  copy.edges.sort(compare);
  const ids = new Set(copy.nodes.map((node) => node.id));
  if (
    !ids.has(copy.root_id) ||
    copy.edges.some((edge) => !ids.has(edge.source_node) || !ids.has(edge.target_node))
  ) {
    throw new Error("Graph contains missing endpoints. Reset the view and retry.");
  }
  return {
    format: "bkp.graph-view.v1",
    app_version: version,
    exported_at: now.toISOString(),
    scope: "visible_graph",
    initial_request: resource,
    notes: [
      "Only currently visible nodes and stored assertions are included; this is not the complete database or biological knowledge.",
      "Expansion and collapse may change the view beyond the initial request; this is not an exact replay recipe or a transactionally consistent database snapshot.",
      "Depth values come from constituent API responses, not a recomputed shortest path in the expanded view. Scanned edges may count repeated candidates.",
      "A sourced association or citation is not proof of causation. Dataset citations retain the first observed source reference even if later metadata change.",
      "exported_at is the browser export time, not the retrieval time of source evidence. Node href values are relative BKP navigation links.",
    ],
    graph: copy,
  };
}

export function graphJSON(snapshot: GraphExport): string {
  return JSON.stringify(snapshot, null, 2) + "\n";
}

const NS = "http://graphml.graphdrawing.org/xmlns";
export function graphML(snapshot: GraphExport): string {
  const doc = document.implementation.createDocument(NS, "graphml", null);
  const root = doc.documentElement;
  function element(name: string, attributes: Record<string, string> = {}) {
    const el = doc.createElementNS(NS, name);
    Object.entries(attributes).forEach(([key, value]) => el.setAttribute(key, value));
    return el;
  }
  const keys: [string, string, string][] = [
    ["metadata", "graph", "metadata_json"],
    ["node_data", "node", "node_json"],
    ["label", "node", "label"],
    ["entity_type", "node", "entity_type"],
    ["assertion", "edge", "assertion_json"],
    ["edge_id", "edge", "bkp_edge_id"],
    ["predicate", "edge", "predicate"],
    ["source", "edge", "source"],
  ];
  for (const [id, scope, name] of keys) {
    root.appendChild(element("key", { id, for: scope, "attr.name": name, "attr.type": "string" }));
  }
  const graph = element("graph", { id: "bkp_view", edgedefault: "directed" });
  root.appendChild(graph);
  function data(parent: Element, key: string, value: string) {
    const el = element("data", { key });
    // XML 1.0 cannot represent these control characters. Refuse rather than lose evidence.
    if (
      [...value].some((char) => {
        const code = char.codePointAt(0)!;
        return (
          (code < 32 && ![9, 10, 13].includes(code)) ||
          (code >= 0xd800 && code <= 0xdfff) ||
          code === 0xfffe ||
          code === 0xffff
        );
      })
    ) {
      throw new Error("This text cannot be represented in GraphML. Use JSON export instead.");
    }
    el.textContent = value;
    parent.appendChild(el);
  }
  const { graph: view, ...metadata } = snapshot;
  data(
    graph,
    "metadata",
    JSON.stringify({
      ...metadata,
      view: {
        root_id: view.root_id,
        limits: view.limits,
        truncated: view.truncated,
        truncation_reasons: view.truncation_reasons,
        scanned_edges: view.scanned_edges,
      },
    }),
  );
  const ids = new Map<string, string>();
  view.nodes.forEach((node, index) => {
    const id = `n${index}`;
    ids.set(node.id, id);
    const el = element("node", { id });
    data(el, "label", node.label);
    data(el, "entity_type", node.entity_type);
    data(el, "node_data", JSON.stringify(node));
    graph.appendChild(el);
  });
  view.edges.forEach((edge, index) => {
    const source = ids.get(edge.source_node),
      target = ids.get(edge.target_node);
    if (!source || !target) throw new Error("Graph contains missing endpoints.");
    const el = element("edge", {
      id: `e${index}`,
      source,
      target,
      directed: String(edge.directed),
    });
    data(el, "edge_id", edge.id);
    data(el, "predicate", edge.assertion.predicate);
    data(el, "source", edge.assertion.source);
    data(el, "assertion", JSON.stringify(edge.assertion));
    graph.appendChild(el);
  });
  return (
    '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(doc) + "\n"
  );
}

export function downloadGraph(snapshot: GraphExport, format: "json" | "graphml"): void {
  const text = format === "json" ? graphJSON(snapshot) : graphML(snapshot);
  const blob = new Blob([text], {
    type:
      format === "json"
        ? "application/json;charset=utf-8"
        : "application/graphml+xml;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `bkp-graph-${snapshot.graph.root_id.replace(/[^a-zA-Z0-9_-]/g, "-")}.${format}`;
  try {
    document.body.appendChild(anchor);
    anchor.click();
  } finally {
    anchor.remove();
    // Give the browser time to start consuming the object URL before releasing it.
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
