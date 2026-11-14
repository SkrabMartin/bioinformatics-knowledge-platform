import { render, screen } from "@testing-library/react";
import { VariantPlacements } from "../components/VariantPlacements";

function response(items: unknown[]) {
  return new Response(
    JSON.stringify({
      items,
      page: 1,
      pages: items.length ? 1 : 0,
      page_size: 10,
      total: items.length,
    }),
    { headers: { "Content-Type": "application/json" } },
  );
}
test("variant placement empty state does not derive coordinates from identifiers", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => response([]));
  render(<VariantPlacements variantId={1} />);
  expect(await screen.findByText(/No sourced genomic placements/)).toBeInTheDocument();
  expect(
    screen.getByText(/does not establish an assembly or genomic position/),
  ).toBeInTheDocument();
});
test("variant placement preserves coordinate interpretation, literal alleles and source release", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    response([
      {
        id: 1,
        variant_id: 2,
        assembly_name: "TEST-ASSEMBLY",
        assembly_accession: "GCA_000000001.1",
        sequence_accession: "TESTSEQ.1",
        sequence_region: "TEST",
        taxonomy_id: "999999",
        coordinate_system: "one_based_closed",
        strand: "+",
        start_position: 10,
        end_position: 11,
        reference_allele: "AC",
        alternate_allele: "A",
        source: "test_source",
        source_identifier: "TEST:placement",
        source_release: "TEST-1",
        source_url: "https://example.test/placement",
        imported_at: "2026-11-11T00:00:00Z",
        created_at: "2026-11-11T00:00:00Z",
        updated_at: "2026-11-11T00:00:00Z",
      },
    ]),
  );
  render(<VariantPlacements variantId={2} />);
  expect(await screen.findByText("TEST-ASSEMBLY · TESTSEQ.1:10–11")).toBeInTheDocument();
  expect(screen.getByText("1-based closed · forward (+) strand")).toBeInTheDocument();
  expect(screen.getByText("AC")).toBeInTheDocument();
  expect(screen.getByText("A")).toBeInTheDocument();
  expect(screen.getByText("TEST-1")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Open provider record/ })).toHaveAttribute(
    "href",
    "https://example.test/placement",
  );
  expect(String(fetch.mock.calls[0][0])).toContain("variants/2/placements?page=1&page_size=10");
});
