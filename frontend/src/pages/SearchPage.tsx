import { Link, useSearchParams } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { SearchResultCard } from "../components/SearchResultCard";
import { ErrorState, LoadingState } from "../components/States";
import { useSearchResults } from "../hooks/useSearchResults";
import type { SearchCounts, SearchEntityType } from "../types/entities";

const categories: {
  value: SearchEntityType | null;
  label: string;
  countKey: keyof SearchCounts;
}[] = [
  { value: null, label: "All results", countKey: "total" },
  { value: "gene", label: "Genes", countKey: "gene" },
  { value: "protein", label: "Proteins", countKey: "protein" },
  { value: "organism", label: "Organisms", countKey: "organism" },
];

export function SearchPage() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q")?.trim() ?? "";
  const requestedType = params.get("type");
  const category: SearchEntityType | null =
    requestedType === "gene" || requestedType === "protein" || requestedType === "organism"
      ? requestedType
      : null;
  const requestedPage = Number(params.get("page") ?? 1);
  const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  const { data, error, loading, retry } = useSearchResults(query, page, category);

  function updateLocation(nextCategory: SearchEntityType | null, nextPage: number) {
    const next = new URLSearchParams({ q: query });
    if (nextCategory) next.set("type", nextCategory);
    if (nextPage > 1) next.set("page", String(nextPage));
    setParams(next);
  }

  return (
    <div className="page-container search-page">
      <PageHeader
        eyebrow="Search workspace"
        title={query ? `Search: ${query}` : "Search biological knowledge"}
        description="Find locally imported genes, proteins, and organisms by symbol, name, accession, or external identifier. Results retain their source context."
        searchValue={query}
      />

      {!query && (
        <section className="search-intro">
          <span className="eyebrow">Start with a known identifier</span>
          <h2>Follow the evidence from a single query.</h2>
          <p>
            Try a gene symbol, UniProt accession, NCBI Gene ID, Ensembl ID, or organism name. Search
            only returns records currently stored in this platform.
          </p>
          <div className="example-queries">
            {["TP53", "P04637", "Homo sapiens"].map((example) => (
              <Link key={example} to={`/search?q=${encodeURIComponent(example)}`}>
                {example} <span aria-hidden="true">↗</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {query && (
        <section aria-live="polite">
          {loading && <LoadingState label="Searching biological records" />}
          {!loading && error && <ErrorState message={error} onRetry={retry} />}
          {!loading && !error && data && (
            <>
              <div className="search-summary">
                <div>
                  <span className="eyebrow">Database results</span>
                  <h2>
                    {data.counts.total.toLocaleString()} matches for “{data.query}”
                  </h2>
                </div>
                <p>
                  Exact identifiers and symbols rank first. Results reflect the current local
                  database, including any labeled demo fixtures.
                </p>
              </div>
              <div className="search-layout">
                <aside className="search-filters" aria-label="Filter results by entity type">
                  <h3>Entity type</h3>
                  {categories.map((item) => (
                    <button
                      key={item.label}
                      aria-pressed={category === item.value}
                      className={category === item.value ? "active" : ""}
                      onClick={() => updateLocation(item.value, 1)}
                      type="button"
                    >
                      <span>{item.label}</span>
                      <strong>{data.counts[item.countKey]}</strong>
                    </button>
                  ))}
                </aside>
                <div className="search-results">
                  {data.items.length > 0 ? (
                    <>
                      <p className="search-result-count">
                        Showing {data.items.length} of {data.total} {category ?? "combined"} results
                      </p>
                      <div className="search-result-list">
                        {data.items.map((item) => (
                          <SearchResultCard
                            key={`${item.entity_type}-${item.entity_id}`}
                            result={item}
                            query={data.query}
                          />
                        ))}
                      </div>
                      <Pagination
                        page={data.page}
                        pages={data.pages}
                        total={data.total}
                        onPageChange={(nextPage) => updateLocation(category, nextPage)}
                      />
                    </>
                  ) : (
                    <div className="search-empty">
                      <span className="state-symbol" aria-hidden="true">
                        ∅
                      </span>
                      <div>
                        <h3>No matching {category ?? "biological"} records</h3>
                        <p>
                          Try a different symbol, accession, or name. Only records in the local
                          database can appear here.
                        </p>
                        {category && (
                          <button
                            className="button button--small"
                            onClick={() => updateLocation(null, 1)}
                            type="button"
                          >
                            View all categories
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </section>
      )}
    </div>
  );
}
