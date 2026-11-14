import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";
const activity = ["gene", "protein", "publication", "dataset"].map((entity_type) => ({
  entity_type,
  jobs: { total: 0 },
  items: { total: 0 },
  last_activity_at: null,
}));
const report = {
  observed_at: "2026-11-14T00:00:00Z",
  worker_status: "unknown",
  scope: "Stored queue counts only",
  activity,
};
function json(body: unknown) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}
function open() {
  render(
    <MemoryRouter initialEntries={["/import-status"]}>
      <App />
    </MemoryRouter>,
  );
}
test("empty queue does not imply empty biological catalogue or an online worker", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json(report));
  open();
  expect(await screen.findByText("No queued import history")).toBeInTheDocument();
  expect(screen.getByText(/Worker availability is unknown/)).toBeInTheDocument();
  expect(screen.getByText(/Biological records may already exist/)).toBeInTheDocument();
  expect(
    screen.getByRole("table", { name: "Import job counts by record type" }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});
test("refresh performs only GET reads and no administrator credential input", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    json({
      ...report,
      activity: activity.map((row) => ({
        ...row,
        jobs: { total: 1, succeeded: 1 },
        items: { total: 2, succeeded: 1, failed: 1 },
        last_activity_at: "2026-11-14T00:00:00Z",
      })),
    }),
  );
  open();
  await screen.findByRole("table", { name: "Import item counts by record type" });
  await userEvent.setup().click(screen.getByRole("button", { name: "Refresh activity" }));
  await screen.findByRole("table", { name: "Import item counts by record type" });
  expect(fetch).toHaveBeenCalledTimes(2);
  for (const [url, options] of fetch.mock.calls) {
    expect(String(url)).toContain("import-status");
    expect(options).not.toHaveProperty("method", "POST");
    expect(options?.headers).not.toHaveProperty("Authorization");
  }
  expect(screen.queryByText("No queued import history")).not.toBeInTheDocument();
});
test("network failure offers retry without fabricating queue state", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("unavailable", { status: 503 }));
  open();
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});
