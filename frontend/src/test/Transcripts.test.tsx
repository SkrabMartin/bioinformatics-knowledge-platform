import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";

const record = {
  id: 1,
  gene_id: 2,
  ensembl_transcript_id: "ENST00000000001",
  version: 1,
  name: "Synthetic transcript",
  biotype: "test-only",
  assembly_name: "DEMO-ASSEMBLY",
  sequence_region: "DEMO",
  start_position: 200,
  end_position: 500,
  strand: "-",
  source: "Ensembl",
  source_identifier: "ENST00000000001",
  source_release: "116",
  source_url: "https://example.test/transcript",
  imported_at: null,
  created_at: "2026-11-07T00:00:00Z",
  updated_at: "2026-11-07T00:00:00Z",
  gene: {
    id: 2,
    symbol: "DEMO-GENE",
    name: "Synthetic gene",
    organism: {
      id: 1,
      scientific_name: "Synthetic organism",
      taxonomy_id: "999999",
      common_name: null,
    },
  },
};
function open(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}
function response(value: unknown) {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

test("transcript browser shows honest empty state", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    response({ items: [], total: 0, page: 1, pages: 0, page_size: 20 }),
  );
  open("/transcripts");
  expect(await screen.findByText(/No transcripts match this view/)).toBeInTheDocument();
});
test("transcript detail retains source release and exact parent taxonomy", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(response(record));
  open("/transcript/ENST00000000001");
  expect(await screen.findByRole("heading", { name: "ENST00000000001" })).toBeInTheDocument();
  expect(screen.getByText("DEMO-ASSEMBLY")).toBeInTheDocument();
  expect(screen.getByText("116")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "DEMO-GENE" })).toHaveAttribute(
    "href",
    "/gene/DEMO-GENE?taxonomy_id=999999",
  );
  expect(screen.getByText(/protein translation are not inferred/)).toBeInTheDocument();
});
test("transcript filter requests local records and retains gene filter", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () =>
      response({ items: [record], total: 1, page: 1, pages: 1, page_size: 20 }),
    );
  open("/transcripts?gene_id=2");
  await screen.findByRole("link", { name: /ENST00000000001/ });
  const user = userEvent.setup();
  await user.type(screen.getByRole("textbox"), "ENST00000000001");
  await user.click(screen.getByRole("button", { name: "Filter transcripts" }));
  expect(
    fetchMock.mock.calls.some(
      ([url]) => String(url).includes("gene_id=2") && String(url).includes("q=ENST00000000001"),
    ),
  ).toBe(true);
});
