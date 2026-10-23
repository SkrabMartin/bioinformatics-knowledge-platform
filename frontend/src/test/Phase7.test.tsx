import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";

const page = (items: unknown[], total = items.length) => ({
  items,
  page: 1,
  page_size: 20,
  total,
  pages: total ? Math.ceil(total / 20) : 0,
});
const response = (data: unknown) =>
  new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
const provenance = {
  source: "development_fixture",
  source_identifier: "demo-knowledge",
  source_release: "test-only-v1",
  source_url: null,
  imported_at: null,
  created_at: "2026-10-23T00:00:00Z",
  updated_at: "2026-10-23T00:00:00Z",
};
const pathway = {
  id: 7,
  name: "Test-only pathway",
  organism_id: null,
  description: "Synthetic pathway, not scientific evidence.",
  ...provenance,
};

function open(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

test("homepage replaces decorative graph with a real local record and actionable context", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    response(
      page([
        {
          id: 3,
          symbol: "DEMO",
          name: "Test-only gene",
          organism: { scientific_name: "Demo organism" },
          source: "development_fixture",
        },
      ]),
    ),
  );
  open("/");
  expect(await screen.findByRole("link", { name: "Explore DEMO" })).toHaveAttribute(
    "href",
    "/graph?type=gene&id=3",
  );
  expect(screen.getByText("Demo organism")).toBeInTheDocument();
  expect(
    screen.getByText("Development example — not authoritative scientific data."),
  ).toBeInTheDocument();
  expect(screen.getByText("No connections are inferred from matching names.")).toBeInTheDocument();
  expect(document.querySelector(".hero-visual")).toBeNull();
});

test("homepage handles unavailable preview with retry and an honest empty database", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockResolvedValueOnce(response(page([])));
  const user = userEvent.setup();
  open("/");
  expect(await screen.findByText("The local record preview is unavailable.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Retry preview" }));
  expect(
    await screen.findByText("No genes are stored yet. Import a source-backed record to begin."),
  ).toBeInTheDocument();
  expect(screen.queryByText("TP53", { exact: true })).not.toBeInTheDocument();
});

test("pathway browser preserves filter URL, provenance and detail navigation", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("relationships")) return response(page([]));
    if (url.includes("pathways/7")) return response(pathway);
    return response(page([pathway]));
  });
  const user = userEvent.setup();
  open("/pathways?q=demo");
  expect(await screen.findByRole("link", { name: "Test-only pathway" })).toHaveAttribute(
    "href",
    "/pathway/7",
  );
  expect(screen.getByText("test-only-v1")).toBeInTheDocument();
  await user.clear(screen.getByRole("textbox", { name: "Filter pathways" }));
  await user.type(screen.getByRole("textbox", { name: "Filter pathways" }), "new-filter");
  await user.click(screen.getByRole("button", { name: "Filter records" }));
  await waitFor(() =>
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("q=new-filter"))).toBe(true),
  );
  await user.click(await screen.findByRole("link", { name: "Test-only pathway" }));
  expect(
    await screen.findByText("Synthetic pathway, not scientific evidence."),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Explore graph ↗" })).toHaveAttribute(
    "href",
    "/graph?type=pathway&id=7",
  );
});

test("ontology detail explains direct hierarchy and shows source release", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
    response(
      String(input).includes("relationships")
        ? page([])
        : { ...pathway, kind: "biological_process", go_id: "GO:9999999" },
    ),
  );
  open("/biological-process/7");
  expect(await screen.findByText("GO:9999999")).toBeInTheDocument();
  expect(screen.getByText(/A term may have multiple parents/)).toBeInTheDocument();
  expect(screen.getByText("test-only-v1")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Explore graph ↗" })).toHaveAttribute(
    "href",
    "/graph?type=biological_process&id=7",
  );
});

test("ontology browser has retry, empty, category navigation and paginated reads", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockResolvedValueOnce(response(page([])));
  const user = userEvent.setup();
  open("/molecular-functions?page=2");
  await user.click(await screen.findByRole("button", { name: "Try again" }));
  expect(await screen.findByText("No molecular functions match this view")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Biological processes" })).toHaveAttribute(
    "href",
    "/biological-processes",
  );
  expect(String(fetchMock.mock.calls[0][0])).toContain(
    "ontology/molecular_function?page=2&page_size=20",
  );
});
