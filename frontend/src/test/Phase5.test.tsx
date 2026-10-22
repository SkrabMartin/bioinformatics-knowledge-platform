import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";

const citation = {
  id: 50,
  pubmed_id: "123456",
  doi: "10.1234/demo",
  title: "Test-only publication title",
  journal: "Synthetic journal",
  abstract: null,
  authors: ["Demo Author"],
  publication_date: "2020",
  publication_date_text: "2020 Winter",
  source: "development_fixture",
  source_identifier: "demo-publication",
  source_url: null,
  imported_at: null,
  created_at: "2026-10-22T00:00:00Z",
  updated_at: "2026-10-22T00:00:00Z",
};
const page = { items: [citation], page: 1, page_size: 12, pages: 1, total: 1 };
const empty = { ...page, items: [], total: 0, pages: 0 };

function response(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}
function open(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

test("publication browser shows citation links and changes shareable sorting", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => response(page));
  const user = userEvent.setup();
  open("/publications?q=demo");
  expect(await screen.findByRole("link", { name: citation.title })).toHaveAttribute(
    "href",
    "/publication/50",
  );
  expect(screen.getByRole("link", { name: /PubMed 123456/ })).toHaveAttribute(
    "href",
    "https://pubmed.ncbi.nlm.nih.gov/123456/",
  );
  await user.selectOptions(screen.getByRole("combobox", { name: "Sort publications" }), "oldest");
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(
        ([url]) => String(url).includes("sort=oldest") && String(url).includes("q=demo"),
      ),
    ).toBe(true),
  );
});

test("publication search submits query and relevance sorting", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => response(page));
  const user = userEvent.setup();
  open("/publications");
  await screen.findByRole("link", { name: citation.title });
  await user.type(screen.getByRole("searchbox", { name: "Search publications" }), "10.1234/demo");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(
        ([url]) =>
          String(url).includes("q=10.1234%2Fdemo") && String(url).includes("sort=relevance"),
      ),
    ).toBe(true),
  );
});

test("publication detail preserves date precision and does not invent an abstract", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    response(String(url).includes("/relationships/") ? empty : citation),
  );
  open("/publication/50");
  expect(await screen.findByRole("heading", { name: citation.title })).toBeInTheDocument();
  expect(screen.getByText("Year only")).toBeInTheDocument();
  expect(screen.getByText("2020 Winter")).toBeInTheDocument();
  expect(screen.getByText("No abstract was supplied by the source.")).toBeInTheDocument();
  expect(
    await screen.findByText("No sourced relationships are stored for this record."),
  ).toBeInTheDocument();
});

test("publication empty and failure states are actionable", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockImplementation(async () => response(empty));
  const user = userEvent.setup();
  open("/publications");
  expect(await screen.findByText("Unable to load this collection")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(
    await screen.findByText(
      "No publications match this view. Only imported citations appear here.",
    ),
  ).toBeInTheDocument();
});

test("gene detail includes sourced publications without inferring claims", async () => {
  const organism = {
    id: 1,
    scientific_name: "Demo species",
    common_name: null,
    taxonomy_id: "999999",
  };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    if (String(url).includes("/publications?")) return response(page);
    if (String(url).includes("/relationships/")) return response(empty);
    return response({
      ...citation,
      id: 1,
      symbol: "DEMO",
      name: "Test-only gene",
      description: null,
      organism,
      chromosome: null,
      start_position: null,
      end_position: null,
      strand: null,
      proteins: [],
      ncbi_gene_id: null,
      ensembl_gene_id: null,
    });
  });
  open("/gene/DEMO?taxonomy_id=999999");
  expect(
    await screen.findByRole("heading", { name: "Associated publications" }),
  ).toBeInTheDocument();
  expect(await screen.findByRole("link", { name: citation.title })).toHaveAttribute(
    "href",
    "/publication/50",
  );
});

test("unified search categorizes publications and safely renders source text", async () => {
  const title = "Synthetic <script>example</script>";
  vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    response({
      query: "example",
      counts: { gene: 0, protein: 0, organism: 0, publication: 1, total: 1 },
      page: 1,
      page_size: 12,
      pages: 1,
      total: 1,
      items: [
        {
          entity_type: "publication",
          entity_id: 50,
          primary_label: title,
          secondary_label: "Demo journal",
          description: null,
          organism: null,
          source: "development_fixture",
          href: "/publication/50",
          score: 400,
          matched_fields: [],
        },
      ],
    }),
  );
  const { container } = open("/search?q=example&type=publication");
  const link = await screen.findByRole("link", { name: /Synthetic/ });
  expect(link.textContent).toBe(title);
  expect(link).toHaveAttribute("href", "/publication/50");
  expect(screen.getByRole("button", { name: "Publications 1" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(container.querySelector("script")).toBeNull();
});
