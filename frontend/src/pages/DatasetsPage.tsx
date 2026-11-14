import { Link, useSearchParams } from "react-router-dom";
import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Page } from "../types/entities";
import type { Dataset } from "../types/datasets";

const columns: Column<Dataset>[] = [
  {
    key: "accession",
    heading: "Accession",
    render: (record) => <span className="mono">{record.accession}</span>,
  },
  {
    key: "title",
    heading: "Title",
    render: (record) => (
      <Link className="entity-link" to={`/dataset/${record.id}`}>
        {record.title}
      </Link>
    ),
  },
  {
    key: "experiment",
    heading: "Experiment type",
    render: (record) => record.experiment_types.join("; ") || "Not supplied",
  },
  {
    key: "samples",
    heading: "Repository samples",
    render: (record) =>
      record.sample_count === null ? (
        "Unavailable"
      ) : (
        <span className="mono">{record.sample_count}</span>
      ),
  },
  {
    key: "source",
    heading: "Source",
    render: (record) => <ProvenanceBadge source={record.source} />,
  },
];

export function DatasetsPage() {
  const [params, setParams] = useSearchParams();
  const value = Number(params.get("page") ?? "1");
  const page = Number.isSafeInteger(value) && value > 0 ? value : 1;
  const query = params.get("q") ?? "";
  const api = new URLSearchParams({ page: String(page), page_size: "20" });
  if (query) api.set("q", query);
  const { data, loading, error, retry } = useEntity<Page<Dataset>>(`datasets?${api}`);
  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Dataset discovery"
        title="Datasets"
        description="Discover imported GEO Series metadata and follow source links to experimental data."
        showSearch={false}
      />
      <form
        className="form-row"
        onSubmit={(event) => {
          event.preventDefault();
          const q = String(new FormData(event.currentTarget).get("q") ?? "").trim();
          setParams(q ? { q } : {});
        }}
      >
        <label>
          Filter by accession, title or source summary
          <input key={query} name="q" defaultValue={query} maxLength={200} />
        </label>
        <button type="submit">Filter datasets</button>
      </form>
      {loading && <LoadingState label="Loading datasets" />}
      {error && <ErrorState message={error} onRetry={retry} />}
      {!loading && !error && data && (
        <>
          {data.items.length ? (
            <DataTable
              caption="Dataset records"
              columns={columns}
              items={data.items}
              getKey={(record) => record.id}
            />
          ) : (
            <EmptyState title="No datasets match this view">
              Only explicitly imported repository metadata appear here.
            </EmptyState>
          )}
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            onPageChange={(next) => {
              const p = new URLSearchParams(params);
              p.set("page", String(next));
              setParams(p);
            }}
          />
        </>
      )}
    </div>
  );
}
