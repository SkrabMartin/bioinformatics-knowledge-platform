import { render, screen } from "@testing-library/react";

import { GeneContextPanel } from "../components/GeneContextPanel";

const provenance = {
  source: "development_fixture",
  source_identifier: "demo-context",
  source_url: null,
  imported_at: "2026-11-07T00:00:00Z",
  created_at: "2026-11-07T00:00:00Z",
  updated_at: "2026-11-07T00:00:00Z",
};

test("empty context does not manufacture aliases or an assembly", () => {
  render(<GeneContextPanel aliases={[]} locations={[]} />);
  expect(screen.getByText("No source-backed aliases have been imported.")).toBeInTheDocument();
  expect(
    screen.getByText("No reference sequence placements have been imported."),
  ).toBeInTheDocument();
  expect(screen.queryByText("GRCh38")).not.toBeInTheDocument();
});

test("source-backed reference observations keep identity and coordinate convention visible", () => {
  render(
    <GeneContextPanel
      aliases={[{ id: 1, alias: "DEMO-ALIAS", ...provenance }]}
      locations={[
        {
          id: 1,
          sequence_accession: "DEMO_SEQ.1",
          chromosome: "DEMO",
          start_position: 10,
          end_position: 20,
          strand: "-",
          ...provenance,
        },
      ]}
    />,
  );
  expect(screen.getByText("DEMO-ALIAS")).toBeInTheDocument();
  expect(screen.getByText("DEMO_SEQ.1")).toBeInTheDocument();
  expect(screen.getAllByText(/development_fixture/)).toHaveLength(2);
  expect(screen.getByText(/one-based inclusive coordinates/)).toBeInTheDocument();
  expect(screen.getByText(/not a genome assembly/)).toBeInTheDocument();
});

test("provider aliases render as text rather than executable markup", () => {
  const { container } = render(
    <GeneContextPanel
      aliases={[{ id: 1, alias: "<script>demo</script>", ...provenance }]}
      locations={[]}
    />,
  );
  expect(screen.getByText("<script>demo</script>")).toBeInTheDocument();
  expect(container.querySelector("script")).toBeNull();
});
