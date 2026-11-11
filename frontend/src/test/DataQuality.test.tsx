import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";

const report = {
  started_at: "2026-11-11T00:00:00Z",
  completed_at: "2026-11-11T00:00:01Z",
  refresh_after_days: 90,
  scope: "Genes and proteins",
  fixture_policy: "Demo fixtures excluded",
  checks: [
    {
      code: "gene_provenance",
      title: "Gene source metadata",
      severity: "warning",
      explanation: "Source context is missing.",
      assessed: 2,
      affected: 1,
      examples: [{ id: 1, label: "TEST", href: "/gene/TEST?taxonomy_id=999999" }],
    },
  ],
};
function open(path = "/data-quality") {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}
function response(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}
test("quality review distinguishes metadata findings and retains organism-specific links", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(response(report));
  open();
  expect(await screen.findByText("Gene source metadata")).toBeInTheDocument();
  expect(screen.getByText(/1 affected \/ 2 assessed/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "TEST" })).toHaveAttribute(
    "href",
    "/gene/TEST?taxonomy_id=999999",
  );
  expect(screen.getByText(/not scientific validity/)).toBeInTheDocument();
});
test("empty review makes no claim about quality", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ ...report, checks: [] }));
  open();
  expect(await screen.findByText(/No records assessed/)).toBeInTheDocument();
});
test("refresh review is submitted as a bounded GET and URL state", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => response(report));
  open();
  await screen.findByText("Gene source metadata");
  const user = userEvent.setup();
  await user.clear(screen.getByRole("spinbutton"));
  await user.type(screen.getByRole("spinbutton"), "30");
  await user.click(screen.getByRole("button", { name: "Review data" }));
  expect(fetch.mock.calls.some(([url]) => String(url).includes("refresh_after_days=30"))).toBe(
    true,
  );
});
