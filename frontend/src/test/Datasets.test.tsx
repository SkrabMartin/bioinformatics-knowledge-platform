import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";

const dataset = {
  id: 1,
  repository: "GEO",
  accession: "GSE999999",
  title: "Synthetic discovery study",
  description: "Test-only source summary",
  experiment_types: ["Test assay"],
  organism_names: ["Synthetic organism"],
  taxonomy_ids: ["999999"],
  platform_accessions: ["GPL999999"],
  publication_pmids: ["123456"],
  sample_count: 2,
  source_updated_date: "2020-01-02",
  source: "development_fixture",
  source_identifier: "GSE999999",
  source_url: "https://example.test/dataset",
  imported_at: "2026-11-12T00:00:00Z",
  created_at: "2026-11-12T00:00:00Z",
  updated_at: "2026-11-12T00:00:00Z",
};
function response(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}
function open(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

test("dataset catalogue uses stored metadata and honest empty states", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    response({ items: [], total: 0, pages: 0, page: 1, page_size: 20 }),
  );
  open("/datasets");
  expect(await screen.findByText(/No datasets match this view/)).toBeInTheDocument();
});
test("dataset detail preserves source counts, dates and external references without inferring patients", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => response(dataset));
  open("/dataset/1");
  expect(
    await screen.findByRole("heading", { name: "Synthetic discovery study" }),
  ).toBeInTheDocument();
  expect(screen.getByText("2020-01-02")).toBeInTheDocument();
  expect(screen.getByText(/not necessarily patients/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "PubMed 123456" })).toHaveAttribute(
    "href",
    "https://pubmed.ncbi.nlm.nih.gov/123456/",
  );
  expect(screen.getByRole("link", { name: /Open GEO record for files/ })).toHaveAttribute(
    "href",
    "https://example.test/dataset",
  );
  expect(screen.getByText(/not downloaded or analyzed/)).toBeInTheDocument();
});
