import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Page } from "../types/entities";
import type { Dataset } from "../types/datasets";

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
        className="publication-controls"
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
          {!data.items.length && (
            <p className="empty-inline">
              No datasets match this view. Only explicitly imported repository metadata appear here.
            </p>
          )}
          <ul className="related-list">
            {data.items.map((record) => (
              <li key={record.id}>
                <Link to={`/dataset/${record.id}`}>
                  <strong>
                    {record.accession} · {record.title}
                  </strong>
                </Link>
                <span>{record.experiment_types.join("; ") || "Experiment type not supplied"}</span>
                <span>
                  {record.sample_count === null
                    ? "Repository sample count unavailable"
                    : `${record.sample_count} repository sample records`}
                </span>
                <ProvenanceBadge source={record.source} />
              </li>
            ))}
          </ul>
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
