import { Link } from "react-router-dom";

import { useEntity } from "../hooks/useEntity";
import type { Gene, Page } from "../types/entities";
import { ProvenanceBadge } from "./ProvenanceBadge";

export function ResearchEntryPanel() {
  const { data, loading, error, retry } = useEntity<Page<Gene>>("genes?page=1&page_size=1");
  const gene = data?.items[0];
  return (
    <aside className="local-record" aria-labelledby="research-entry-title">
      <h2 id="research-entry-title">Stored gene record</h2>
      <div className="local-record-body" aria-live="polite">
        {loading ? (
          <p>Loading the first stored gene…</p>
        ) : error ? (
          <>
            <p>The local record preview is unavailable.</p>
            <button type="button" onClick={retry}>
              Retry preview
            </button>
          </>
        ) : gene ? (
          <>
            <div className="local-record-top">
              <span className="entity-type">Gene</span>
              <ProvenanceBadge source={gene.source} />
            </div>
            <h3>{gene.symbol}</h3>
            <p>{gene.name}</p>
            <p>
              <i>{gene.organism.scientific_name}</i>
            </p>
            <Link className="button" to={`/graph?type=gene&id=${gene.id}`}>
              Open {gene.symbol} in graph
            </Link>
            {gene.source === "development_fixture" && (
              <p className="context-note">
                Development example — not authoritative scientific data.
              </p>
            )}
          </>
        ) : (
          <>
            <p>No genes are stored yet. Import a source-backed record to begin.</p>
            <Link to="/about">Read scope and data policy</Link>
          </>
        )}
      </div>
      <ol className="steps">
        <li>
          <strong>Search</strong>
          <span>Check the identifier and organism of a record.</span>
        </li>
        <li>
          <strong>Graph</strong>
          <span>Expand only relationships stored locally.</span>
        </li>
        <li>
          <strong>Source</strong>
          <span>Open the provider record behind each assertion.</span>
        </li>
      </ol>
      <p className="context-note">No connections are inferred from matching names.</p>
    </aside>
  );
}
