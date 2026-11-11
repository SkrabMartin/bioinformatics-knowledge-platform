import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Page } from "../types/entities";
import type { Phenotype } from "../types/phenotypes";

export function PhenotypesPage() {
  const [params, setParams] = useSearchParams();
  const value = Number(params.get("page") ?? "1");
  const page = Number.isSafeInteger(value) && value > 0 ? value : 1;
  const query = params.get("q") ?? "";
  const api = new URLSearchParams({ page: String(page), page_size: "20" });
  if (query) api.set("q", query);
  const { data, loading, error, retry } = useEntity<Page<Phenotype>>(`phenotypes?${api}`);
  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Diseases and phenotypes"
        title="Phenotypes"
        description="Browse stored HPO-identified phenotype terms and their source metadata."
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
          Filter by HPO ID or name
          <input key={query} name="q" defaultValue={query} maxLength={200} />
        </label>
        <button type="submit">Filter phenotypes</button>
      </form>
      {loading && <LoadingState label="Loading phenotypes" />}
      {error && <ErrorState message={error} onRetry={retry} />}
      {!loading && !error && data && (
        <>
          {!data.items.length && (
            <p className="empty-inline">
              No phenotypes match this view. Only explicitly stored source terms appear here;
              automatic HPO ingestion is not enabled.
            </p>
          )}
          <ul className="related-list">
            {data.items.map((record) => (
              <li key={record.id}>
                <Link to={`/phenotype/${record.id}`}>
                  <strong>
                    {record.hpo_id} · {record.name}
                  </strong>
                </Link>
                <span>Release {record.source_release}</span>
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
