import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";

const record = {
  id: 1,
  pubmed_id: "123456",
  doi: null,
  title: "Synthetic literature",
  journal: "Test journal",
  authors: [],
  abstract: null,
  publication_date: "2020",
  publication_date_text: "2020",
  keywords: ["CytometryOnly", "žluťoučký"],
  source: "development_fixture",
  source_identifier: "TEST",
  source_url: null,
  imported_at: null,
  created_at: "2026-11-12T00:00:00Z",
  updated_at: "2026-11-12T00:00:00Z",
};
function response(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}
function open() {
  render(
    <MemoryRouter initialEntries={["/publication/1"]}>
      <App />
    </MemoryRouter>,
  );
}
function mock(value: unknown) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    response(
      String(url).includes("relationships")
        ? { items: [], total: 0, page: 1, pages: 0, page_size: 10 }
        : value,
    ),
  );
}

test("source keywords are visible and link to publication-filtered search", async () => {
  mock(record);
  open();
  expect(await screen.findByRole("heading", { name: "Source keywords" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "CytometryOnly" })).toHaveAttribute(
    "href",
    "/search?q=CytometryOnly&type=publication",
  );
  expect(screen.getByRole("link", { name: "žluťoučký" })).toHaveAttribute(
    "href",
    `/search?q=${encodeURIComponent("žluťoučký")}&type=publication`,
  );
  expect(screen.getByText(/not inferred topics/)).toBeInTheDocument();
});
test("missing source keywords remain an explicit empty metadata state", async () => {
  mock({ ...record, keywords: [] });
  open();
  expect(
    await screen.findByText("No source keywords are stored for this record."),
  ).toBeInTheDocument();
});
