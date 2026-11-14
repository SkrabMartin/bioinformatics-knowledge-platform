import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";

function response(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}
function page(items: unknown[]) {
  return { items, total: items.length, page: 1, page_size: 20, pages: items.length ? 1 : 0 };
}
function open(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}
const term = {
  id: 1,
  go_id: "GO:9999901",
  name: "Synthetic cellular component",
  kind: "cellular_component",
  description: "Test-only source term",
  source: "development_fixture",
  source_identifier: "TEST:term",
  source_release: "TEST-1",
  source_url: "https://example.test/term",
  imported_at: null,
  created_at: "2026-11-12T00:00:00Z",
  updated_at: "2026-11-12T00:00:00Z",
};

test("cellular component catalogue is source-backed and empty without imported terms", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => response(page([])));
  open("/cellular-components");
  expect(await screen.findByRole("heading", { name: "Cellular components" })).toBeInTheDocument();
  expect(String(fetch.mock.calls[0][0])).toContain("ontology/cellular_component");
  expect(await screen.findByText(/No cellular components/)).toBeInTheDocument();
});
test("component detail preserves aspect, release, direct protein evidence and graph navigation", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    response(
      String(url).includes("/relationships/")
        ? page([
            {
              relationship_type: "protein_cellular_component",
              relationship_id: 1,
              predicate: "annotated_to",
              subject: {
                entity_type: "protein",
                entity_id: 2,
                label: "TEST-PROTEIN",
                href: "/protein/TEST-PROTEIN",
              },
              object: {
                entity_type: "cellular_component",
                entity_id: 1,
                label: "Synthetic cellular component",
                href: "/cellular-component/1",
              },
              source: "development_fixture",
              source_identifier: "TEST:annotation",
              source_release: "TEST-1",
              evidence_code: "IDA",
              evidence_kind: "curated",
              evidence_text: "Test-only annotation",
              source_url: null,
              imported_at: null,
              provenance_basis: "relationship_assertion",
              created_at: "2026-11-12T00:00:00Z",
              updated_at: "2026-11-12T00:00:00Z",
            },
          ])
        : term,
    ),
  );
  open("/cellular-component/1");
  expect(
    await screen.findByRole("heading", { name: "Synthetic cellular component" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("annotated to (source assertion)")).toBeInTheDocument();
  expect(screen.getByText("cellular component")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "TEST-PROTEIN" })).toHaveAttribute(
    "href",
    "/protein/TEST-PROTEIN",
  );
  expect(screen.getByRole("link", { name: /Explore graph/ })).toHaveAttribute(
    "href",
    "/graph?type=cellular_component&id=1",
  );
});
