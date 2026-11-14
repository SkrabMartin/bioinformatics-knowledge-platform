import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";
const gene = {
  id: 2,
  symbol: "BRCA1",
  name: "Synthetic test record",
  href: "/gene/BRCA1?taxonomy_id=9606",
  source: "development_fixture",
  source_identifier: "test",
  source_url: "https://example.test/gene",
  imported_at: null,
  updated_at: "2026-11-14T00:00:00Z",
};
const input = {
  input_count: 2,
  unique_inputs: ["TP53", "BRCA1"],
  duplicates_removed: 0,
  unresolved: [],
  matched_inputs: { TP53: 1, BRCA1: 2 },
  resolved_gene_count: 2,
};
const report = {
  method: "exact_local_gene_set_overlap_v1",
  software_version: "0.23.0",
  computed_at: "2026-11-14T00:00:00Z",
  namespace: "symbol",
  taxonomy_id: "9606",
  coverage_complete: true,
  left: input,
  right: input,
  metrics: { left_size: 2, right_size: 2, intersection_size: 1, union_size: 3, jaccard: 1 / 3 },
  shared: [gene],
  left_only: [],
  right_only: [],
  interpretation: "Descriptive overlap only; no enrichment or p-value.",
};
function response(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}
function open() {
  render(
    <MemoryRouter initialEntries={["/analysis/gene-overlap"]}>
      <App />
    </MemoryRouter>,
  );
}
async function submit() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Use local human example" }));
  await user.click(screen.getByRole("button", { name: "Compare gene lists" }));
  return user;
}
test("overlap runs only after explicit submission and preserves bounded exact inputs", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => response(report));
  open();
  expect(fetch).not.toHaveBeenCalled();
  const user = await submit();
  expect(await screen.findByRole("link", { name: "BRCA1" })).toHaveAttribute(
    "href",
    "/gene/BRCA1?taxonomy_id=9606",
  );
  const params = new URL(String(fetch.mock.calls[0][0]), "https://example.test").searchParams;
  expect(params.getAll("left")).toEqual(["TP53", "BRCA1"]);
  expect(params.getAll("right")).toEqual(["BRCA1", "PINK1"]);
  expect(params.get("taxonomy_id")).toBe("9606");
  expect(screen.getByText("0.3333")).toBeInTheDocument();
  expect(screen.getByText(/no enrichment or p-value/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Compare gene lists" }));
  await screen.findByText("0.3333");
  expect(fetch).toHaveBeenCalledTimes(2);
});
test("partial empty resolution is not displayed as a zero Jaccard score", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    response({
      ...report,
      coverage_complete: false,
      left: { ...input, unresolved: ["UNKNOWN"], matched_inputs: {}, resolved_gene_count: 0 },
      right: { ...input, unresolved: ["UNKNOWN"], matched_inputs: {}, resolved_gene_count: 0 },
      metrics: { left_size: 0, right_size: 0, intersection_size: 0, union_size: 0, jaccard: null },
      shared: [],
    }),
  );
  open();
  await submit();
  expect(await screen.findByText("Undefined (empty resolved union)")).toBeInTheDocument();
  expect(screen.getByText(/Partial resolution/)).toBeInTheDocument();
  expect(screen.getAllByText("UNKNOWN")).toHaveLength(2);
});
test("oversized input is rejected before any request", async () => {
  const fetch = vi.spyOn(globalThis, "fetch");
  open();
  const user = userEvent.setup();
  await user.type(
    screen.getByRole("textbox", { name: "Left gene list" }),
    Array(51).fill("TP53").join(","),
  );
  await user.type(screen.getByRole("textbox", { name: "Right gene list" }), "BRCA1");
  await user.click(screen.getByRole("button", { name: "Compare gene lists" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("1–50");
  expect(fetch).not.toHaveBeenCalled();
});
test("server errors do not invent an analysis or enable export", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("unavailable", { status: 503 }));
  open();
  await submit();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Download analysis JSON" })).not.toBeInTheDocument();
});
