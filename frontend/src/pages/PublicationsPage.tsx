import { useSearchParams } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { PublicationCard } from "../components/PublicationCard";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Page, Publication } from "../types/entities";

export function PublicationsPage() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const requestedPage = Number(params.get("page") ?? "1");
  const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  const requestedSort = params.get("sort");
  const sort =
    requestedSort === "oldest" || requestedSort === "relevance" ? requestedSort : "newest";
  const apiParams = new URLSearchParams({ page: String(page), page_size: "12", sort });
  if (query) apiParams.set("q", query);
  const geneId = params.get("gene_id");
  if (geneId) apiParams.set("gene_id", geneId);
  const { data, loading, error, retry } = useEntity<Page<Publication>>(`publications?${apiParams}`);

  function update(values: Record<string, string>) {
    const next = new URLSearchParams(params);
    Object.entries(values).forEach(([key, value]) =>
      value ? next.set(key, value) : next.delete(key),
    );
    setParams(next);
  }

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Scientific literature"
        title="Publications"
        description="Explore locally imported citations. Source links describe provider metadata or curated assertions, not proof of causation."
        showSearch={false}
      />
      <form
        className="publication-controls"
        onSubmit={(event) => {
          event.preventDefault();
          const value = String(new FormData(event.currentTarget).get("q") ?? "").trim();
          update({ q: value, page: "", sort: "relevance" });
        }}
      >
        <label>
          Search publications
          <input
            aria-label="Search publications"
            type="search"
            key={query}
            defaultValue={query}
            name="q"
            maxLength={200}
            placeholder="Title, abstract, journal, PMID or DOI"
          />
        </label>
        <button type="submit" className="button">
          Search
        </button>
        <label>
          Sort publications
          <select value={sort} onChange={(event) => update({ sort: event.target.value, page: "" })}>
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="relevance">Relevance</option>
          </select>
        </label>
      </form>
      {geneId && (
        <p className="context-note">
          Showing publications linked to gene #{geneId}.{" "}
          <button type="button" onClick={() => update({ gene_id: "", page: "" })}>
            Clear gene filter
          </button>
        </p>
      )}
      <section aria-live="polite">
        {loading && <LoadingState label="Loading publications" />}
        {!loading && error && <ErrorState message={error} onRetry={retry} />}
        {!loading && !error && data && (
          <>
            {data.items.length === 0 ? (
              <p className="context-note">
                No publications match this view. Only imported citations appear here.
              </p>
            ) : (
              <div className="publication-list">
                {data.items.map((publication) => (
                  <PublicationCard key={publication.id} publication={publication} />
                ))}
              </div>
            )}
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              onPageChange={(next) => update({ page: String(next) })}
            />
          </>
        )}
      </section>
    </div>
  );
}
