import { useState } from "react";
import { Link } from "react-router-dom";

import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useEntityPage } from "../hooks/useEntityPage";
import type { Gene } from "../types/entities";

const columns: Column<Gene>[] = [
  {
    key: "gene",
    heading: "Gene",
    render: (gene) => (
      <div className="primary-cell">
        <Link
          className="entity-link"
          to={`/gene/${encodeURIComponent(gene.symbol)}?taxonomy_id=${encodeURIComponent(gene.organism.taxonomy_id ?? "9606")}`}
        >
          {gene.symbol}
        </Link>
        <span>{gene.name}</span>
      </div>
    ),
  },
  {
    key: "organism",
    heading: "Organism",
    render: (gene) => (
      <div className="stacked-cell">
        <i>{gene.organism.scientific_name}</i>
        <small>{gene.organism.common_name ?? "—"}</small>
      </div>
    ),
  },
  {
    key: "location",
    heading: "Location",
    render: (gene) => (gene.chromosome ? `Chr ${gene.chromosome}` : "Not available"),
  },
  {
    key: "identifiers",
    heading: "External identifiers",
    render: (gene) => (
      <div className="stacked-cell identifiers">
        <span>{gene.ncbi_gene_id ?? "No NCBI Gene ID"}</span>
        <small>{gene.ensembl_gene_id ?? "No Ensembl ID"}</small>
      </div>
    ),
  },
  {
    key: "source",
    heading: "Source",
    render: (gene) => <ProvenanceBadge source={gene.source} />,
  },
];

export function GenesPage() {
  const [page, setPage] = useState(1);
  const { data, error, loading, retry } = useEntityPage<Gene>("genes", page);

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Entity browser"
        title="Genes"
        description="Inspect normalized gene records with organism context and explicit source metadata."
      />
      <section aria-live="polite">
        {loading && <LoadingState label="Loading genes" />}
        {!loading && error && <ErrorState message={error} onRetry={retry} />}
        {!loading && !error && data?.items.length === 0 && <EmptyState entity="genes" />}
        {!loading && !error && data && data.items.length > 0 && (
          <>
            <DataTable
              caption="Gene records"
              columns={columns}
              items={data.items}
              getKey={(gene) => gene.id}
            />
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              onPageChange={setPage}
            />
          </>
        )}
      </section>
    </div>
  );
}
