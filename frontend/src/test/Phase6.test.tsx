import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";
import { collapseBranch, mergeGraph } from "../features/graph/state";
import type { GraphEdge, GraphNode, GraphResponse } from "../features/graph/types";

// jsdom has no browser canvas. Actual renderer is verified in the browser separately.
vi.mock("../features/graph/GraphCanvas", () => ({
  GraphCanvas: () => <div role="img" aria-label="Graph canvas test substitute" />,
}));

function node(id: number, type: GraphNode["entity_type"] = "protein"): GraphNode {
  return {
    id: `${type}:${id}`,
    entity_type: type,
    entity_id: id,
    label: `Demo ${type} ${id}`,
    href: type === "gene" ? "/gene/DEMO" : `/${type}/${id}`,
    depth: type === "gene" ? 0 : 1,
  };
}
const gene = node(1, "gene"),
  protein = node(1),
  partner = node(2);
function edge(id: number, from = gene, to = protein): GraphEdge {
  return {
    id: `gene_protein:${id}`,
    source_node: from.id,
    target_node: to.id,
    directed: true,
    assertion: {
      relationship_type: "gene_protein",
      relationship_id: id,
      predicate: "encodes",
      subject: from,
      object: to,
      source: "development_fixture",
      source_identifier: `demo-source-${id}`,
      source_url: "https://example.test/evidence",
      evidence_text: "Test-only evidence; not scientific fact.",
      evidence_kind: null,
      provenance_basis: "protein_record",
      imported_at: null,
      created_at: "2026-10-23T00:00:00Z",
      updated_at: "2026-10-23T00:00:00Z",
    },
  };
}
const initial: GraphResponse = {
  root_id: gene.id,
  nodes: [gene, protein],
  edges: [edge(1)],
  limits: { depth: 1, max_nodes: 60, max_edges: 120, entity_types: [], relationship_types: [] },
  truncated: false,
  truncation_reasons: [],
  scanned_edges: 1,
};
const expanded: GraphResponse = {
  ...initial,
  root_id: protein.id,
  nodes: [protein, partner],
  edges: [edge(2, protein, partner)],
};
function json(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}
function open(path = "/graph?type=gene&id=1") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

test("merging graphs preserves typed IDs, parallel sources and global budgets", () => {
  const duplicate = mergeGraph(initial, initial);
  expect(duplicate.nodes).toHaveLength(2);
  expect(duplicate.edges).toHaveLength(1);
  const parallel = mergeGraph(initial, { ...initial, edges: [edge(2)] });
  expect(parallel.edges).toHaveLength(2);
  const capped = mergeGraph({ ...initial, limits: { ...initial.limits, max_nodes: 2 } }, expanded);
  expect(capped.nodes).toHaveLength(2);
  expect(capped.edges).toHaveLength(1);
  expect(capped.truncation_reasons).toContain("node_limit");
  const edgeCapped = mergeGraph(
    { ...initial, limits: { ...initial.limits, max_edges: 1 } },
    expanded,
  );
  expect(edgeCapped.edges).toHaveLength(1);
  expect(edgeCapped.nodes).toHaveLength(2);
  expect(edgeCapped.truncation_reasons).toContain("edge_limit");
});

test("collapse prunes a branch but retains shared nodes reachable on another path", () => {
  const graph = mergeGraph(initial, expanded);
  expect(collapseBranch(graph, protein.id).nodes.map((item) => item.id)).toEqual([
    gene.id,
    protein.id,
  ]);
  const shared = mergeGraph(graph, {
    ...initial,
    nodes: [gene, partner],
    edges: [edge(3, gene, partner)],
  });
  expect(collapseBranch(shared, protein.id).nodes).toHaveLength(3);
  expect(collapseBranch(shared, gene.id).nodes).toEqual([gene]);
});

test("graph inspector is keyboard accessible and exposes source provenance", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => json(initial));
  const user = userEvent.setup();
  open();
  expect(await screen.findByText("2 nodes · 1 relationships")).toBeInTheDocument();
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Inspect relationship" }),
    "gene_protein:1",
  );
  expect(screen.getByText("demo-source-1")).toBeInTheDocument();
  expect(screen.getByText("Inherited from protein record")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Open relationship source/ })).toHaveAttribute(
    "href",
    "https://example.test/evidence",
  );
  expect(screen.getByText("Test-only evidence; not scientific fact.")).toBeInTheDocument();
});

test("expanding and collapsing nodes keeps navigation and graph state usable", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    json(String(url).includes("graph/protein/1") ? expanded : initial),
  );
  const user = userEvent.setup();
  open();
  await screen.findByText("2 nodes · 1 relationships");
  await user.selectOptions(screen.getByRole("combobox", { name: "Inspect node" }), protein.id);
  expect(screen.getByRole("link", { name: /Open entity page/ })).toHaveAttribute(
    "href",
    "/protein/1",
  );
  await user.click(screen.getByRole("button", { name: "Expand node" }));
  expect(await screen.findByText("3 nodes · 2 relationships")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Collapse branch" }));
  expect(await screen.findByText("2 nodes · 1 relationships")).toBeInTheDocument();
});

test("expansion failure preserves the existing graph and allows retry", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    if (String(url).includes("graph/protein/1")) throw new TypeError("offline");
    return json(initial);
  });
  const user = userEvent.setup();
  open();
  await screen.findByText("2 nodes · 1 relationships");
  await user.selectOptions(screen.getByRole("combobox", { name: "Inspect node" }), protein.id);
  await user.click(screen.getByRole("button", { name: "Expand node" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("existing graph is preserved");
  expect(screen.getByText("2 nodes · 1 relationships")).toBeInTheDocument();
  fetchMock.mockImplementation(async () => json(expanded));
  await user.click(screen.getByRole("button", { name: "Expand node" }));
  expect(await screen.findByText("3 nodes · 2 relationships")).toBeInTheDocument();
});

test("graph query controls use shareable URLs and cancel stale requests", async () => {
  const requests: { url: string; signal?: AbortSignal | null }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, options) => {
    requests.push({ url: String(url), signal: options?.signal });
    return json(initial);
  });
  const user = userEvent.setup();
  open();
  await screen.findByText("2 nodes · 1 relationships");
  await user.selectOptions(screen.getByRole("combobox", { name: "Initial depth" }), "2");
  await waitFor(() => expect(requests.some((item) => item.url.includes("depth=2"))).toBe(true));
  expect(requests[0].signal?.aborted).toBe(true);
});

test("partial and empty graph states do not imply missing biological evidence", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    json({
      ...initial,
      nodes: [gene],
      edges: [],
      truncated: true,
      truncation_reasons: ["node_limit"],
    }),
  );
  open();
  expect(await screen.findByText(/Partial graph: Node limit reached/)).toBeInTheDocument();
  expect(
    screen.getByText(/does not establish the absence of biological connections/),
  ).toBeInTheDocument();
});

test("graph failures retry and gene symbol entry uses the explicit lookup route", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockImplementation(async () => json(initial));
  const user = userEvent.setup();
  open("/graph");
  await user.type(screen.getByRole("textbox", { name: "Gene symbol" }), "DEMO");
  await user.click(screen.getByRole("button", { name: "Explore gene" }));
  expect(await screen.findByText("Unable to load this collection")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("2 nodes · 1 relationships")).toBeInTheDocument();
  expect(
    fetchMock.mock.calls.some(([url]) => String(url).includes("graph/gene/by-symbol/DEMO")),
  ).toBe(true);
});
