import { useState } from "react";
import { Link } from "react-router-dom";

import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useEntityPage } from "../hooks/useEntityPage";
import type { Disease } from "../types/entities";

const columns: Column<Disease>[] = [
  {
    key: "disease",
    heading: "Disease",
    render: (disease) => (
      <div className="primary-cell">
        <Link className="entity-link" to={`/disease/${disease.id}`}>
          {disease.name}
        </Link>
        <span>{disease.description ?? "No source description supplied"}</span>
      </div>
    ),
  },
  {
    key: "identifiers",
    heading: "Ontology identifiers",
    render: (disease) => (
      <div className="stacked-cell identifiers">
        <span>{disease.mondo_id ?? "No MONDO ID"}</span>
        <small>{disease.disease_ontology_id ?? "No Disease Ontology ID"}</small>
      </div>
    ),
  },
  {
    key: "source",
    heading: "Source",
    render: (disease) => <ProvenanceBadge source={disease.source} />,
  },
];

export function DiseasesPage() {
  const [page, setPage] = useState(1);
  const { data, error, loading, retry } = useEntityPage<Disease>("diseases", page);

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Entity browser"
        title="Diseases"
        description="Inspect sourced disease concepts and follow their locally recorded gene and variant associations."
      />
      <section aria-live="polite">
        {loading && <LoadingState label="Loading diseases" />}
        {!loading && error && <ErrorState message={error} onRetry={retry} />}
        {!loading && !error && data?.items.length === 0 && <EmptyState entity="diseases" />}
        {!loading && !error && data && data.items.length > 0 && (
          <>
            <DataTable
              caption="Disease records"
              columns={columns}
              items={data.items}
              getKey={(disease) => disease.id}
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
