import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";
import { PhenotypeAnnotations } from "../components/PhenotypeAnnotations";

const source = {
  source: "test_source",
  source_identifier: "TEST",
  source_release: "TEST-1",
  source_url: "https://example.test/source",
  imported_at: "2026-11-11T00:00:00Z",
  created_at: "2026-11-11T00:00:00Z",
  updated_at: "2026-11-11T00:00:00Z",
};
const phenotype = {
  ...source,
  id: 1,
  hpo_id: "HP:0000001",
  name: "Synthetic phenotype",
  description: "Test-only term",
};
const annotation = {
  ...source,
  id: 1,
  disease_id: 2,
  phenotype_id: 1,
  qualifier: "excluded",
  evidence_kind: "structured_metadata",
  evidence_code: "TEST",
  reference: "TEST:reference",
  phenotype,
  disease: {
    ...source,
    id: 2,
    name: "Synthetic disease",
    description: null,
    mondo_id: null,
    disease_ontology_id: null,
  },
};
function response(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}
function page(items: unknown[]) {
  return { items, page: 1, page_size: 20, total: items.length, pages: items.length ? 1 : 0 };
}
function open(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

test("phenotype catalogue makes the empty source-data state explicit", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => response(page([])));
  open("/phenotypes");
  expect(await screen.findByText(/No phenotypes match this view/)).toBeInTheDocument();
  expect(screen.getByText(/automatic HPO ingestion is not enabled/)).toBeInTheDocument();
});
test("phenotype detail retains source release and excluded disease assertions", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    response(String(url).includes("/diseases?") ? page([annotation]) : phenotype),
  );
  open("/phenotype/1");
  expect(await screen.findByRole("heading", { name: "Synthetic phenotype" })).toBeInTheDocument();
  expect(await screen.findByText("Excluded phenotype (source assertion)")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Synthetic disease" })).toHaveAttribute(
    "href",
    "/disease/2",
  );
  expect(screen.getByText(/TEST:reference/)).toBeInTheDocument();
});
test("disease panel preserves conflicting positive and excluded assertions", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    response(page([annotation, { ...annotation, id: 2, qualifier: "present" }])),
  );
  render(
    <MemoryRouter>
      <PhenotypeAnnotations kind="disease" id={2} />
    </MemoryRouter>,
  );
  expect(await screen.findByText("Excluded phenotype (source assertion)")).toBeInTheDocument();
  expect(screen.getByText("Present phenotype (source assertion)")).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "HP:0000001 · Synthetic phenotype" })).toHaveLength(2);
});
