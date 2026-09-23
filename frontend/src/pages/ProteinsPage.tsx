import { useState } from "react";
import { Link } from "react-router-dom";

import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useEntityPage } from "../hooks/useEntityPage";
import type { Protein } from "../types/entities";

const columns: Column<Protein>[] = [
  {
    key: "protein",
    heading: "Protein",
    render: (protein) => (
      <div className="primary-cell">
        <Link className="entity-link" to={`/protein/${encodeURIComponent(protein.accession)}`}>
          {protein.accession}
        </Link>
        <span>{protein.name}</span>
      </div>
    ),
  },
  {
    key: "gene",
    heading: "Encoded by",
    render: (protein) => protein.gene?.symbol ?? "Not linked",
  },
  {
    key: "organism",
    heading: "Organism",
    render: (protein) => <i>{protein.organism.scientific_name}</i>,
  },
  {
    key: "length",
    heading: "Length",
    render: (protein) =>
      protein.sequence_length ? `${protein.sequence_length} aa` : "Not available",
  },
  {
    key: "source",
    heading: "Source",
    render: (protein) => <ProvenanceBadge source={protein.source} />,
  },
];

export function ProteinsPage() {
  const [page, setPage] = useState(1);
  const { data, error, loading, retry } = useEntityPage<Protein>("proteins", page);

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Entity browser"
        title="Proteins"
        description="Browse normalized protein accessions and their current gene and organism links."
      />
      <section aria-live="polite">
        {loading && <LoadingState label="Loading proteins" />}
        {!loading && error && <ErrorState message={error} onRetry={retry} />}
        {!loading && !error && data?.items.length === 0 && <EmptyState entity="proteins" />}
        {!loading && !error && data && data.items.length > 0 && (
          <>
            <DataTable
              caption="Protein records"
              columns={columns}
              items={data.items}
              getKey={(protein) => protein.id}
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
