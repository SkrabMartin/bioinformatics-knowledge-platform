import type { GraphResponse, TruncationReason } from "./types";

export function mergeGraph(current: GraphResponse, addition: GraphResponse): GraphResponse {
  const nodes = new Map(current.nodes.map((node) => [node.id, node]));
  const edges = new Map(current.edges.map((edge) => [edge.id, edge]));
  const candidates = new Map(addition.nodes.map((node) => [node.id, node]));
  const reasons = new Set<TruncationReason>([
    ...current.truncation_reasons,
    ...addition.truncation_reasons,
  ]);
  for (const edge of addition.edges) {
    const endpoints = [...new Set([edge.source_node, edge.target_node])];
    if (endpoints.some((id) => !nodes.has(id) && !candidates.has(id))) continue;
    const newIds = endpoints.filter((id) => !nodes.has(id));
    if (nodes.size + newIds.length > current.limits.max_nodes) {
      reasons.add("node_limit");
      continue;
    }
    if (!edges.has(edge.id) && edges.size >= current.limits.max_edges) {
      reasons.add("edge_limit");
      continue;
    }
    for (const id of endpoints) {
      const node = candidates.get(id);
      if (node && !nodes.has(id)) nodes.set(id, node);
    }
    edges.set(edge.id, edge);
  }
  return {
    ...current,
    nodes: [...nodes.values()],
    edges: [...edges.values()],
    truncated: reasons.size > 0,
    truncation_reasons: [...reasons],
    scanned_edges: current.scanned_edges + addition.scanned_edges,
  };
}

export function collapseBranch(graph: GraphResponse, barrier: string): GraphResponse {
  const adjacency = new Map<string, Set<string>>();
  for (const edge of graph.edges) {
    for (const [from, to] of [
      [edge.source_node, edge.target_node],
      [edge.target_node, edge.source_node],
    ]) {
      if (!adjacency.has(from)) adjacency.set(from, new Set());
      adjacency.get(from)!.add(to);
    }
  }
  const visible = new Set([graph.root_id]);
  const queue = [graph.root_id];
  for (let i = 0; i < queue.length; i++) {
    const id = queue[i];
    if (id === barrier) continue;
    for (const neighbor of adjacency.get(id) ?? []) {
      if (!visible.has(neighbor)) {
        visible.add(neighbor);
        queue.push(neighbor);
      }
    }
  }
  return {
    ...graph,
    nodes: graph.nodes.filter((node) => visible.has(node.id)),
    edges: graph.edges.filter(
      (edge) => visible.has(edge.source_node) && visible.has(edge.target_node),
    ),
  };
}

export function graphParams(
  limits: GraphResponse["limits"],
  depth = limits.depth,
): URLSearchParams {
  const params = new URLSearchParams({
    depth: String(depth),
    max_nodes: String(limits.max_nodes),
    max_edges: String(limits.max_edges),
  });
  limits.entity_types.forEach((type) => params.append("type", type));
  limits.relationship_types.forEach((type) => params.append("relationship_type", type));
  return params;
}
