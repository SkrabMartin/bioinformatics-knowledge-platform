import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";

const genePage = {
  items: [
    {
      id: 1,
      symbol: "TP53",
      name: "Tumor protein p53",
      description: "Development fixture",
      organism_id: 1,
      organism: {
        id: 1,
        scientific_name: "Homo sapiens",
        common_name: "Human",
        taxonomy_id: "9606",
      },
      chromosome: "17",
      start_position: null,
      end_position: null,
      strand: null,
      ncbi_gene_id: "demo-ncbi-7157",
      ensembl_gene_id: "demo-ensembl-TP53",
      source: "development_fixture",
      source_identifier: "demo-gene-TP53",
      source_url: null,
      imported_at: null,
      created_at: "2026-09-20T00:00:00Z",
      updated_at: "2026-09-20T00:00:00Z",
    },
  ],
  page: 1,
  page_size: 10,
  total: 1,
  pages: 1,
};

function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

test("renders API-backed gene records and provenance", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(genePage), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

  renderApp("/genes");

  expect(screen.getByText("Loading genes")).toBeInTheDocument();
  expect(await screen.findByText("TP53")).toBeInTheDocument();
  expect(screen.getByText("Demo fixture")).toBeInTheDocument();
  expect(screen.getByText("1 total records")).toBeInTheDocument();
});

test("renders and retries an actionable API error", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockResolvedValueOnce(
      new Response(JSON.stringify(genePage), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  const user = userEvent.setup();

  renderApp("/genes");
  expect(await screen.findByText("Unable to load this collection")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  expect(await screen.findByText("TP53")).toBeInTheDocument();
});

const searchResponse = {
  query: "TP53",
  items: [
    {
      entity_type: "gene",
      entity_id: 1,
      primary_label: "TP53",
      secondary_label: "tumor protein p53",
      description: "A source-provided description of TP53.",
      organism: { scientific_name: "Homo sapiens", taxonomy_id: "9606" },
      source: "NCBI Gene",
      href: "/gene/TP53?taxonomy_id=9606",
      score: 1200,
      matched_fields: [{ field: "symbol", value: "TP53" }],
    },
    {
      entity_type: "protein",
      entity_id: 2,
      primary_label: "P04637",
      secondary_label: "Cellular tumor antigen p53",
      description: "Source-provided protein function.",
      organism: { scientific_name: "Homo sapiens", taxonomy_id: "9606" },
      source: "UniProt",
      href: "/protein/P04637",
      score: 850,
      matched_fields: [{ field: "gene_symbol", value: "TP53" }],
    },
  ],
  counts: { gene: 1, protein: 1, organism: 0, total: 2 },
  page: 1,
  page_size: 12,
  total: 2,
  pages: 1,
};

test("renders ranked search results, categories, highlighting, and provenance", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(searchResponse), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  renderApp("/search?q=TP53");

  expect(screen.getByRole("heading", { name: "Search: TP53" })).toBeInTheDocument();
  expect(await screen.findByText("2 matches for “TP53”")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "TP53" })).toHaveAttribute(
    "href",
    "/gene/TP53?taxonomy_id=9606",
  );
  expect(screen.getByRole("link", { name: "P04637" })).toHaveAttribute("href", "/protein/P04637");
  expect(screen.getAllByText("TP53", { selector: "mark" }).length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "Genes 1" })).toBeInTheDocument();
  expect(screen.getByText("NCBI Gene")).toBeInTheDocument();
  expect(String(fetchMock.mock.calls[0][0])).toContain("/search?q=TP53&page=1&page_size=12");
});

test("filters search categories with a shareable URL", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    const filtered = url.includes("type=protein");
    return new Response(
      JSON.stringify({
        ...searchResponse,
        items: filtered ? [searchResponse.items[1]] : searchResponse.items,
        total: filtered ? 1 : 2,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  });
  const user = userEvent.setup();
  renderApp("/search?q=TP53");

  await screen.findByText("2 matches for “TP53”");
  await user.click(screen.getByRole("button", { name: "Proteins 1" }));

  await waitFor(() =>
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("type=protein"))).toBe(true),
  );
  expect(await screen.findByText("Showing 1 of 1 protein results")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Proteins 1" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

test("shows empty and retryable search states", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("offline"));
  fetchMock.mockResolvedValueOnce(
    new Response(
      JSON.stringify({
        ...searchResponse,
        items: [],
        counts: { gene: 0, protein: 0, organism: 0, total: 0 },
        total: 0,
        pages: 0,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );
  const user = userEvent.setup();
  renderApp("/search?q=TP53");

  expect(await screen.findByText("Unable to load this collection")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("No matching biological records")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test("offers API-backed search suggestions", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        query: "TP",
        items: [
          {
            entity_type: "gene",
            value: "TP53",
            secondary_label: "tumor protein p53",
            href: "/gene/TP53?taxonomy_id=9606",
          },
        ],
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );
  const user = userEvent.setup();
  renderApp("/search");

  await user.type(screen.getByRole("searchbox", { name: "Search biological entities" }), "TP");
  expect(await screen.findByRole("link", { name: /TP53 tumor protein p53/ })).toHaveAttribute(
    "href",
    "/gene/TP53?taxonomy_id=9606",
  );
  expect(String(fetchMock.mock.calls[0][0])).toContain("/search/suggestions?q=TP&limit=8");
});

test("renders a gene detail page with linked protein and provenance", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        ...genePage.items[0],
        description: "NCBI-provided gene summary.",
        start_position: 7668422,
        end_position: 7687491,
        strand: "-",
        ncbi_gene_id: "7157",
        source: "NCBI Gene",
        source_identifier: "7157",
        source_url: "https://www.ncbi.nlm.nih.gov/gene/7157",
        imported_at: "2026-09-20T12:00:00Z",
        proteins: [{ id: 2, accession: "P04637", name: "Cellular tumor antigen p53" }],
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );

  renderApp("/gene/TP53");

  expect(await screen.findByRole("heading", { name: "TP53" })).toBeInTheDocument();
  expect(screen.getByText("NCBI-provided gene summary.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /P04637/ })).toHaveAttribute("href", "/protein/P04637");
  expect(screen.getByRole("link", { name: /Open provider record/ })).toHaveAttribute(
    "href",
    "https://www.ncbi.nlm.nih.gov/gene/7157",
  );
});

test("renders a protein detail page with its encoding gene", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        id: 2,
        accession: "P04637",
        name: "Cellular tumor antigen p53",
        gene_id: 1,
        gene: { id: 1, symbol: "TP53", name: "tumor protein p53" },
        organism_id: 1,
        organism: genePage.items[0].organism,
        function: "UniProt-provided function statement.",
        sequence_length: 393,
        source: "UniProt",
        source_identifier: "P04637",
        source_url: "https://www.uniprot.org/uniprotkb/P04637/entry",
        imported_at: "2026-09-20T12:00:00Z",
        created_at: "2026-09-20T12:00:00Z",
        updated_at: "2026-09-20T12:00:00Z",
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );

  renderApp("/protein/P04637");

  expect(await screen.findByRole("heading", { name: "P04637" })).toBeInTheDocument();
  expect(screen.getByText("393 amino acids")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /TP53/ })).toHaveAttribute(
    "href",
    "/gene/TP53?taxonomy_id=9606",
  );
});
