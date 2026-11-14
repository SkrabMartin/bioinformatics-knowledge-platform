import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";

const kinds = [
  ["transcript", "Transcript", "/transcript/ENST00000000001"],
  ["disease", "Disease", "/disease/1"],
  ["variant", "Variant", "/variant/1"],
  ["pathway", "Pathway", "/pathway/1"],
  ["biological_process", "Biological process", "/biological-process/1"],
  ["molecular_function", "Molecular function", "/molecular-function/2"],
];
function response() {
  return new Response(
    JSON.stringify({
      query: "shared",
      page: 1,
      page_size: 12,
      total: 6,
      pages: 1,
      counts: {
        gene: 0,
        protein: 0,
        organism: 0,
        publication: 0,
        transcript: 1,
        disease: 1,
        variant: 1,
        pathway: 1,
        biological_process: 1,
        molecular_function: 1,
        total: 6,
      },
      items: kinds.map(([kind, label, href], i) => ({
        entity_type: kind,
        entity_id: i + 1,
        primary_label: "shared " + label,
        secondary_label: null,
        description: "Synthetic search record",
        organism: null,
        source: "test_source",
        href,
        score: 400,
        matched_fields: [],
      })),
    }),
    { headers: { "Content-Type": "application/json" } },
  );
}
function open(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}
test("new search catalogues show typed results, source labels and detail links", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => response());
  open("/search?q=shared");
  await screen.findByRole("link", { name: "shared Transcript" });
  for (const [, label, href] of kinds) {
    expect(screen.getByRole("link", { name: "shared " + label })).toHaveAttribute("href", href);
  }
  expect(screen.getByRole("button", { name: /Biological processes/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Molecular functions/ })).toBeInTheDocument();
});
test("transcript category is shareable and switching categories updates the request", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => response());
  open("/search?q=shared&type=transcript");
  await screen.findByRole("link", { name: "shared Transcript" });
  expect(screen.getByRole("button", { name: /Transcripts/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(String(fetch.mock.calls[0][0])).toContain("type=transcript");
  await userEvent.setup().click(screen.getByRole("button", { name: /Pathways/ }));
  await waitFor(() =>
    expect(fetch.mock.calls.some(([url]) => String(url).includes("type=pathway"))).toBe(true),
  );
});
