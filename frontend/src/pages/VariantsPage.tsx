import { useState } from "react";
import { Link } from "react-router-dom";

import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useEntityPage } from "../hooks/useEntityPage";
import type { Variant } from "../types/entities";

const columns: Column<Variant>[] = [
  {
    key: "variant",
    heading: "Variant",
    render: (variant) => (
      <div className="primary-cell">
        <Link className="entity-link" to={`/variant/${variant.id}`}>
          {variant.rsid ?? variant.hgvs}
        </Link>
        <span>{variant.description ?? "No source description supplied"}</span>
      </div>
    ),
  },
  {
    key: "organism",
    heading: "Organism",
    render: (variant) => <i>{variant.organism.scientific_name}</i>,
  },
  {
    key: "identifiers",
    heading: "Identifiers",
    render: (variant) => (
      <div className="stacked-cell identifiers">
        <span>{variant.rsid ?? "No rsID"}</span>
        <small>{variant.hgvs ?? "No HGVS expression"}</small>
      </div>
    ),
  },
  {
    key: "source",
    heading: "Source",
    render: (variant) => <ProvenanceBadge source={variant.source} />,
  },
];

export function VariantsPage() {
  const [page, setPage] = useState(1);
  const { data, error, loading, retry } = useEntityPage<Variant>("variants", page);

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Entity browser"
        title="Variants"
        description="Browse sourced variant identifiers and inspect evidence-linked genes and diseases."
      />
      <section aria-live="polite">
        {loading && <LoadingState label="Loading variants" />}
        {!loading && error && <ErrorState message={error} onRetry={retry} />}
        {!loading && !error && data?.items.length === 0 && <EmptyState entity="variants" />}
        {!loading && !error && data && data.items.length > 0 && (
          <>
            <DataTable
              caption="Variant records"
              columns={columns}
              items={data.items}
              getKey={(variant) => variant.id}
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
