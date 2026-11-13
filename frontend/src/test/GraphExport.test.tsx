import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { GraphWorkspace } from "../features/graph/GraphWorkspace";
import * as exports from "../features/graph/export";
import { collapseBranch } from "../features/graph/state";
import type { GraphResponse } from "../features/graph/types";
vi.mock("../features/graph/GraphCanvas", () => ({
  GraphCanvas: () => <div>Canvas substitute</div>,
}));
const first = {
  id: "dataset:1",
  entity_type: "dataset" as const,
  entity_id: 1,
  label: 'Test <&> "český"',
  href: "/dataset/1",
  depth: 0,
};
const second = {
  id: "publication:1",
  entity_type: "publication" as const,
  entity_id: 1,
  label: "Test citation",
  href: "/publication/1",
  depth: 1,
};
const graph: GraphResponse = {
  root_id: first.id,
  nodes: [second, first],
  edges: [
    {
      id: "dataset_publication:1",
      source_node: first.id,
      target_node: second.id,
      directed: true,
      assertion: {
        relationship_type: "dataset_publication",
        relationship_id: 1,
        predicate: "cites",
        subject: first,
        object: second,
        source: "development_fixture <&>",
        source_identifier: "test",
        source_url: "https://example.test/?a=1&b=2",
        imported_at: "2026-01-01T00:00:00Z",
        source_record_date: "2020-01-02",
        evidence_text: "Synthetic </data><script>test</script>",
        evidence_kind: "structured_metadata",
        provenance_basis: "relationship_assertion",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    },
  ],
  limits: { depth: 1, max_nodes: 60, max_edges: 120, entity_types: [], relationship_types: [] },
  truncated: true,
  truncation_reasons: ["scan_limit"],
  scanned_edges: 1000,
};
const resource = "graph/dataset/1?depth=1";
test("JSON retains provenance, limits, scope and separate browser export timestamp", () => {
  const result = exports.captureGraph(graph, resource, new Date("2026-11-13T00:00:00Z"));
  const parsed = JSON.parse(exports.graphJSON(result));
  expect(parsed.graph.edges[0].assertion).toEqual(graph.edges[0].assertion);
  expect(parsed.graph.truncation_reasons).toEqual(["scan_limit"]);
  expect(parsed.scope).toBe("visible_graph");
  expect(parsed.initial_request).toBe(resource);
  expect(parsed.exported_at).toBe("2026-11-13T00:00:00.000Z");
  result.graph.nodes[0].label = "Changed";
  expect(first.label).not.toBe("Changed");
});
test("collapsed exports omit hidden branches while retaining partial status", () => {
  const view = exports.captureGraph(collapseBranch(graph, first.id), resource);
  expect(view.graph.nodes.map((n) => n.id)).toEqual([first.id]);
  expect(view.graph.edges).toEqual([]);
  expect(view.graph.truncated).toBe(true);
  expect(view.notes.join(" ")).toContain("not the complete database");
});
test("GraphML roundtrip escapes Unicode and XML text and retains evidence and mixed directions", () => {
  const view = structuredClone(graph);
  view.edges.push({ ...view.edges[0], id: "parallel:2", directed: false, target_node: first.id });
  const doc = new DOMParser().parseFromString(
    exports.graphML(exports.captureGraph(view, resource)),
    "application/xml",
  );
  expect(doc.querySelector("parsererror")).toBeNull();
  expect(doc.documentElement.namespaceURI).toBe("http://graphml.graphdrawing.org/xmlns");
  expect(doc.querySelectorAll("node")).toHaveLength(2);
  expect(doc.querySelectorAll("edge")).toHaveLength(2);
  expect(doc.querySelector('data[key="label"]')!.textContent).toBe(first.label);
  expect(JSON.parse(doc.querySelector('data[key="assertion"]')!.textContent!)).toEqual(
    graph.edges[0].assertion,
  );
  const edge = doc.querySelector('edge[directed="false"]')!;
  expect(edge.getAttribute("source")).toBe(edge.getAttribute("target"));
  expect(
    JSON.parse(doc.querySelector('data[key="metadata"]')!.textContent!).view.truncation_reasons,
  ).toEqual(["scan_limit"]);
  expect(doc.querySelector("script")).toBeNull();
});
test("missing endpoints fail closed and XML-incompatible text has lossless JSON fallback", () => {
  expect(() => exports.captureGraph({ ...graph, nodes: [first] }, resource)).toThrow(
    /missing endpoints/,
  );
  const view = structuredClone(graph);
  view.nodes[0].label = "Invalid\u0001text";
  const snapshot = exports.captureGraph(view, resource);
  expect(() => exports.graphML(snapshot)).toThrow(/Use JSON/);
  expect(
    JSON.parse(exports.graphJSON(snapshot)).graph.nodes.some((n: { label: string }) =>
      n.label.includes("\u0001"),
    ),
  ).toBe(true);
});
test("download removes anchor and releases object URL after consumption starts", () => {
  vi.useFakeTimers();
  const create = vi.fn((blob: Blob) => {
      expect(blob.type).toContain("application/json");
      return "blob:test";
    }),
    revoke = vi.fn();
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: create });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revoke });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  try {
    exports.downloadGraph(exports.captureGraph(graph, resource), "json");
    expect(click).toHaveBeenCalledOnce();
    expect(create.mock.calls[0][0].type).toContain("application/json");
    expect(document.querySelector("a[download]")).toBeNull();
    expect(revoke).not.toHaveBeenCalled();
    vi.runAllTimers();
    expect(revoke).toHaveBeenCalledWith("blob:test");
  } finally {
    vi.useRealTimers();
    Reflect.deleteProperty(URL, "createObjectURL");
    Reflect.deleteProperty(URL, "revokeObjectURL");
  }
});
function open() {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(graph), { headers: { "Content-Type": "application/json" } }),
  );
  render(
    <MemoryRouter>
      <GraphWorkspace resource={resource} />
    </MemoryRouter>,
  );
}
test("workspace downloads only the current collapsed view", async () => {
  const download = vi.spyOn(exports, "downloadGraph").mockImplementation(() => {});
  open();
  const user = userEvent.setup();
  await screen.findByRole("button", { name: "Download JSON" });
  await user.click(screen.getByRole("button", { name: "Collapse branch" }));
  await user.click(screen.getByRole("button", { name: "Download JSON" }));
  expect(download.mock.calls[0][0].graph.nodes).toHaveLength(1);
  expect(download.mock.calls[0][0].graph.edges).toHaveLength(0);
  expect(screen.getByText(/not a complete database export/)).toBeInTheDocument();
});
test("download errors remain accessible and preserve the displayed graph", async () => {
  vi.spyOn(exports, "downloadGraph").mockImplementation(() => {
    throw new Error("Use JSON export instead.");
  });
  open();
  const user = userEvent.setup();
  await screen.findByRole("button", { name: "Download GraphML" });
  await user.click(screen.getByRole("button", { name: "Download GraphML" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Use JSON");
  expect(screen.getByText("2 nodes · 1 relationships")).toBeInTheDocument();
});
