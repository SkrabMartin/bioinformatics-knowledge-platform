import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { SimilarNames } from "../components/SimilarNames";
function open(query = "Homo sapines", category: string | null = null) {
  render(
    <MemoryRouter>
      <SimilarNames query={query} category={category} />
    </MemoryRouter>,
  );
}
test("name hints are opt-in, source-labeled and distinct from scientific confidence", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        query: "Homo sapines",
        items: [
          {
            entity_type: "organism",
            entity_id: 1,
            label: "Homo sapiens",
            matched_name: "Homo sapiens",
            match_field: "scientific_name",
            source: "development_fixture",
            href: "/search?q=Homo+sapiens&type=organism",
            similarity: 0.75,
          },
        ],
      }),
      { headers: { "Content-Type": "application/json" } },
    ),
  );
  open();
  expect(fetch).not.toHaveBeenCalled();
  await userEvent.setup().click(screen.getByRole("button", { name: "Find similar names" }));
  expect(await screen.findByRole("link", { name: "Homo sapiens" })).toHaveAttribute(
    "href",
    "/search?q=Homo+sapiens&type=organism",
  );
  expect(screen.getByText(/not identifier corrections/)).toBeInTheDocument();
  expect(screen.getByText(/Text similarity score/)).toBeInTheDocument();
  expect(String(fetch.mock.calls[0][0])).toContain("name-suggestions?");
});
test("identifiers and unsupported categories never request fuzzy correction", () => {
  const fetch = vi.spyOn(globalThis, "fetch");
  open("TP53");
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});
test("failed name hints expose retry rather than fabricated empty matches", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("unavailable", { status: 503 }));
  open("mitochodrial", "gene");
  await userEvent.setup().click(screen.getByRole("button", { name: "Find similar names" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByText(/No similar stored names met/)).not.toBeInTheDocument();
});
