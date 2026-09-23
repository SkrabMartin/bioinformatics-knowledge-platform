import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";

const provenance = {
  source: "development_fixture",
  source_identifier: "demo-source",
  source_url: null,
  imported_at: null,
  created_at: "2026-09-21T00:00:00Z",
  updated_at: "2026-09-21T00:00:00Z",
};

const disease = {
  ...provenance,
  id: 5,
  name: "Demo condition",
  description: "Test-only disease record.",
  mondo_id: null,
  disease_ontology_id: null,
};

const variant = {
  ...provenance,
  id: 7,
  rsid: null,
  hgvs: "DEMO:variant-1",
  description: "Test-only variant record.",
  organism_id: 1,
  organism: { id: 1, scientific_name: "Homo sapiens", common_name: "Human", taxonomy_id: "9606" },
};

const relationship = {
  relationship_type: "gene_disease",
  relationship_id: 12,
  predicate: "associated_with",
  subject: {
    entity_type: "gene",
    entity_id: 3,
    label: "DEMO1",
    href: "/gene/DEMO1?taxonomy_id=9606",
  },
  object: { entity_type: "disease", entity_id: 5, label: "Demo condition", href: "/disease/5" },
  ...provenance,
  evidence_text: "Test-only association; not scientific evidence.",
  provenance_basis: "relationship_assertion",
};

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function renderRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

test("lists sourced diseases without inventing associations", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    jsonResponse({ items: [disease], page: 1, page_size: 10, total: 1, pages: 1 }),
  );
  renderRoute("/diseases");

  expect(await screen.findByRole("link", { name: "Demo condition" })).toHaveAttribute(
    "href",
    "/disease/5",
  );
  expect(screen.getByText("Demo fixture")).toBeInTheDocument();
  expect(screen.getByText("No MONDO ID")).toBeInTheDocument();
});

test("disease detail shows sourced relationship evidence and navigation", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input) =>
      String(input).includes("/relationships/disease/5")
        ? jsonResponse({ items: [relationship], page: 1, page_size: 10, total: 1, pages: 1 })
        : jsonResponse(disease),
    );
  renderRoute("/disease/5");

  expect(await screen.findByRole("heading", { name: "Demo condition" })).toBeInTheDocument();
  expect(
    await screen.findByText("Test-only association; not scientific evidence."),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "DEMO1" })).toHaveAttribute(
    "href",
    "/gene/DEMO1?taxonomy_id=9606",
  );
  expect(
    fetchMock.mock.calls.some(([url]) => String(url).includes("/relationships/disease/5")),
  ).toBe(true);
});

test("variant detail shows identifiers and an honest empty relationship state", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
    String(input).includes("/relationships/variant/7")
      ? jsonResponse({ items: [], page: 1, page_size: 10, total: 0, pages: 0 })
      : jsonResponse(variant),
  );
  renderRoute("/variant/7");

  expect(await screen.findByRole("heading", { name: "DEMO:variant-1" })).toBeInTheDocument();
  expect(
    await screen.findByText("No sourced relationships are stored for this record."),
  ).toBeInTheDocument();
  expect(screen.getByText("Homo sapiens")).toBeInTheDocument();
});
