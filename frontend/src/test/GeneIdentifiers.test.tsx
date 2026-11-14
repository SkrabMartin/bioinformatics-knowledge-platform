import { render, screen } from "@testing-library/react";
import { GeneIdentifierPanel } from "../components/GeneIdentifierPanel";

test("empty registry does not invent provenance for legacy identifiers", () => {
  render(<GeneIdentifierPanel identifiers={[]} />);
  expect(screen.getByText(/No source-backed identifier assertions/)).toBeInTheDocument();
  expect(screen.queryByText("Ensembl Gene")).not.toBeInTheDocument();
});

test("mapping display separates stable identity and source-reported versions", () => {
  render(
    <GeneIdentifierPanel
      identifiers={[
        {
          id: 1,
          namespace: "ensembl_gene",
          accession: "ENSG00000000001",
          evidence: [
            {
              id: 2,
              source: "UniProt",
              source_identifier: "TEST-ONLY",
              source_url: "https://example.test",
              reported_accession: "ENSG00000000001.20",
              source_record_version: "42",
              imported_at: null,
              created_at: "2026-11-11T00:00:00Z",
              updated_at: "2026-11-11T00:00:00Z",
            },
          ],
        },
      ]}
    />,
  );
  expect(screen.getByText("Ensembl Gene · ENSG00000000001")).toBeInTheDocument();
  expect(screen.getByText("Reported identifier: ENSG00000000001.20")).toBeInTheDocument();
  expect(screen.getByText("Provider record version: 42")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View mapping source" })).toHaveAttribute(
    "href",
    "https://example.test",
  );
});
