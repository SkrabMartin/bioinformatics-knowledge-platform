import { Link, useSearchParams } from "react-router-dom";
import { DataTable, type Column } from "../components/DataTable";
import { KnowledgeNavigation } from "../components/KnowledgeNavigation";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { ErrorState, LoadingState } from "../components/States";
import { knowledgeCollections } from "../features/knowledge/config";
import { useEntity } from "../hooks/useEntity";
import type { KnowledgeKind, OntologyTerm, Page, Pathway } from "../types/entities";

type KnowledgeRecord = OntologyTerm | Pathway;

export function KnowledgeBrowserPage({ kind }: { kind: KnowledgeKind }) {
  const collection = knowledgeCollections[kind];
  const [params, setParams] = useSearchParams();
  const pageNumber = Number(params.get("page") ?? "1");
  const page = Number.isSafeInteger(pageNumber) && pageNumber > 0 ? pageNumber : 1;
  const query = params.get("q") ?? "";
  const apiParams = new URLSearchParams({ page: String(page), page_size: "20" });
  if (query) apiParams.set("q", query);
  const { data, loading, error, retry } = useEntity<Page<KnowledgeRecord>>(
    `${collection.resource}?${apiParams}`,
  );
  const columns: Column<KnowledgeRecord>[] = [
    {
      key: "name",
      heading: "Record",
      render: (record) => (
        <div className="primary-cell">
          <Link className="entity-link" to={`${collection.detail}/${record.id}`}>
            {record.name}
          </Link>
          <span>{"go_id" in record ? record.go_id : record.source_identifier}</span>
        </div>
      ),
    },
    { key: "release", heading: "Source release", render: (record) => record.source_release },
    {
      key: "source",
      heading: "Source",
      render: (record) => <ProvenanceBadge source={record.source} />,
    },
  ];
  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Functional knowledge"
        title={collection.title}
        description={collection.description}
        showSearch={false}
      />
      <KnowledgeNavigation />
      <form
        className="knowledge-search"
        onSubmit={(event) => {
          event.preventDefault();
          const q = String(new FormData(event.currentTarget).get("q") ?? "").trim();
          setParams(q ? { q } : {});
        }}
      >
        <label>
          Filter {collection.title.toLowerCase()}
          <input
            key={query}
            name="q"
            defaultValue={query}
            maxLength={200}
            placeholder="Name or source identifier"
          />
        </label>
        <button type="submit" className="button">
          Filter records
        </button>
      </form>
      <p className="context-note">
        Direct, source-backed records only. No enrichment scores or inferred ancestor annotations
        are calculated.
      </p>
      {loading && <LoadingState label={`Loading ${collection.title.toLowerCase()}`} />}
      {!loading && error && <ErrorState message={error} onRetry={retry} />}
      {!loading &&
        !error &&
        data &&
        (data.items.length ? (
          <>
            <DataTable
              caption={`${collection.title} records`}
              columns={columns}
              items={data.items}
              getKey={(record) => record.id}
            />
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              onPageChange={(value) => {
                const next = new URLSearchParams(params);
                next.set("page", String(value));
                setParams(next);
              }}
            />
          </>
        ) : (
          <div className="knowledge-empty">
            <h2>No {collection.title.toLowerCase()} match this view</h2>
            <p>
              A fresh installation contains no pathway or GO assertions. Add source-backed records
              using the administrator API; no biological data is invented.
            </p>
          </div>
        ))}
    </div>
  );
}
