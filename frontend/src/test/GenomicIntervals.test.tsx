import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";
const transcript = {
  id: 1,
  ensembl_transcript_id: "ENST00000000001",
  version: 1,
  assembly_name: "TESTv1",
  sequence_region: "DEMO",
  start_position: 100,
  end_position: 200,
  strand: "-",
  source: "Ensembl",
  source_release: "test",
  gene: { organism: { taxonomy_id: "999993" } },
};
const report = {
  query: {
    assembly_name: "TESTv1",
    sequence_region: "DEMO",
    taxonomy_id: "999993",
    coordinate_system: "one_based_closed",
  },
  normalized_start: 100,
  normalized_end: 200,
  method: "local_transcript_span_overlap_v1",
  interpretation: "Whole transcript spans only; not exon overlap.",
  observed_at: "2026-11-14T00:00:00Z",
  matches: {
    page: 1,
    page_size: 20,
    total: 1,
    pages: 1,
    items: [
      {
        ...transcript,
        gene_symbol: "DEMO",
        gene_href: "/gene/DEMO?taxonomy_id=999993",
        transcript_href: "/transcript/ENST00000000001",
        overlap_start: 100,
        overlap_end: 200,
        overlap_bases: 101,
      },
    ],
  },
};
function json(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}
function open() {
  render(
    <MemoryRouter initialEntries={["/genomics/intervals"]}>
      <App />
    </MemoryRouter>,
  );
}
function mock(reportOverride = report) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input) =>
      String(input).includes("transcripts?")
        ? json({ items: [transcript], total: 1, page: 1, page_size: 1, pages: 1 })
        : json(reportOverride),
    );
}
async function submit() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Use stored transcript example" }));
  await screen.findByText(/Example from stored transcript/);
  await user.click(screen.getByRole("button", { name: "Browse transcript spans" }));
  return user;
}
test("interval example comes from stored metadata and search remains explicit", async () => {
  const fetch = mock();
  open();
  expect(fetch).not.toHaveBeenCalled();
  await submit();
  expect(await screen.findByRole("link", { name: "ENST00000000001.1" })).toHaveAttribute(
    "href",
    "/transcript/ENST00000000001",
  );
  const url = new URL(String(fetch.mock.calls[1][0]), "https://example.test");
  expect(url.searchParams.get("assembly_name")).toBe("TESTv1");
  expect(url.searchParams.get("taxonomy_id")).toBe("999993");
  expect(url.searchParams.get("start")).toBe("100");
  expect(screen.getByText(/not exon overlap/)).toBeInTheDocument();
  expect(screen.getByText(/reference axis/)).toBeInTheDocument();
});
test("zero-based input is explicitly transmitted and results label normalized coordinates", async () => {
  const fetch = mock();
  open();
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Use stored transcript example" }));
  await screen.findByText(/Example from stored transcript/);
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Input coordinates" }),
    "zero_based_half_open",
  );
  await user.clear(screen.getByRole("spinbutton", { name: "Start" }));
  await user.type(screen.getByRole("spinbutton", { name: "Start" }), "99");
  await user.click(screen.getByRole("button", { name: "Browse transcript spans" }));
  await screen.findByRole("table");
  const params = new URL(String(fetch.mock.calls[1][0]), "https://example.test").searchParams;
  expect(params.get("start")).toBe("99");
  expect(params.get("coordinate_system")).toBe("zero_based_half_open");
  expect(screen.getByText(/does not convert them automatically/)).toBeInTheDocument();
});
test("empty coverage makes no biological absence claim", async () => {
  mock({ ...report, matches: { ...report.matches, total: 0, pages: 0, items: [] } });
  open();
  await submit();
  expect(await screen.findByText(/does not establish biological absence/)).toBeInTheDocument();
});
test("unavailable stored example does not invent a reference interval", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [], total: 0 }));
  open();
  await userEvent
    .setup()
    .click(screen.getByRole("button", { name: "Use stored transcript example" }));
  expect(await screen.findByText(/No usable stored transcript example/)).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "Assembly name" })).toHaveValue("");
});
