import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Page, Transcript } from "../types/entities";

export function TranscriptsPage() {
  const [params, setParams] = useSearchParams();
  const requested = Number(params.get("page") ?? "1");
  const page = Number.isSafeInteger(requested) && requested > 0 ? requested : 1;
  const query = params.get("q") ?? "";
  const api = new URLSearchParams({ page: String(page), page_size: "20" });
  if (query) api.set("q", query);
  const geneId = Number(params.get("gene_id"));
  if (Number.isSafeInteger(geneId) && geneId > 0) api.set("gene_id", String(geneId));
  const { data, loading, error, retry } = useEntity<Page<Transcript>>("transcripts?" + api);
  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Gene annotations"
        title="Transcripts"
        description="Browse imported Ensembl transcript annotations with their parent gene, assembly and source release."
        showSearch={false}
      />
      <form
        className="publication-controls"
        onSubmit={(event) => {
          event.preventDefault();
          const next = new URLSearchParams(params);
          const q = String(new FormData(event.currentTarget).get("q") ?? "").trim();
          if (q) next.set("q", q);
          else next.delete("q");
          next.delete("page");
          setParams(next);
        }}
      >
        <label>
          Filter by transcript ID, transcript name or gene symbol
          <input name="q" defaultValue={query} maxLength={200} key={query} />
        </label>
        <button type="submit">Filter transcripts</button>
      </form>
      {loading && <LoadingState label="Loading transcripts" />}
      {error && <ErrorState message={error} onRetry={retry} />}
      {!loading && !error && data && (
        <>
          {data.items.length ? (
            <ul className="related-list">
              {data.items.map((record) => (
                <li key={record.id}>
                  <Link to={"/transcript/" + encodeURIComponent(record.ensembl_transcript_id)}>
                    <strong>
                      {record.ensembl_transcript_id}
                      {record.version ? "." + record.version : ""}
                    </strong>
                    <span>
                      {record.name ?? "No source display name"} · {record.gene.symbol}
                    </span>
                    <span>
                      {record.assembly_name} · Ensembl release {record.source_release}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-inline">
              No transcripts match this view. Only imported source annotations appear here.
            </p>
          )}
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
      )}
    </div>
  );
}
