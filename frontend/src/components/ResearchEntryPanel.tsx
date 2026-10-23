import { Link } from "react-router-dom";

import { useEntity } from "../hooks/useEntity";
import type { Gene, Page } from "../types/entities";
import { ProvenanceBadge } from "./ProvenanceBadge";

export function ResearchEntryPanel() {
  const { data, loading, error, retry } = useEntity<Page<Gene>>("genes?page=1&page_size=1");
  const gene = data?.items[0];
  return (
    <aside className="research-entry" aria-labelledby="research-entry-title">
      <div className="research-entry-heading">
        <span className="eyebrow">A starting point, from your database</span>
        <h2 id="research-entry-title">Follow a record. Inspect the evidence.</h2>
      </div>
      <div className="research-entry-record" aria-live="polite">
        {loading ? (
          <p>Finding a local starting point…</p>
        ) : error ? (
          <>
            <p>The local record preview is unavailable.</p>
            <button type="button" onClick={retry}>
              Retry preview
            </button>
          </>
        ) : gene ? (
          <>
            <div className="research-entry-record-top">
              <span className="research-entry-type">Gene · local record</span>
              <ProvenanceBadge source={gene.source} />
            </div>
            <h3>{gene.symbol}</h3>
            <p>{gene.name}</p>
            <span className="research-entry-organism">{gene.organism.scientific_name}</span>
            <Link className="research-entry-cta" to={`/graph?type=gene&id=${gene.id}`}>
              Explore {gene.symbol} <span aria-hidden="true">↗</span>
            </Link>
            {gene.source === "development_fixture" && (
              <p className="research-entry-note">
                Development example — not authoritative scientific data.
              </p>
            )}
          </>
        ) : (
          <>
            <h3>Your research starts with a record.</h3>
            <p>No genes are stored yet. Import a source-backed record to begin.</p>
            <Link className="research-entry-cta" to="/about">
              Understand the platform ↗
            </Link>
          </>
        )}
      </div>
      <ol className="research-entry-steps">
        <li>
          <span>01</span>
          <div>
            <strong>Find the right entity</strong>
            <p>Check its identifier and organism.</p>
          </div>
        </li>
        <li>
          <span>02</span>
          <div>
            <strong>Follow stored connections</strong>
            <p>Expand only relationships recorded locally.</p>
          </div>
        </li>
        <li>
          <span>03</span>
          <div>
            <strong>Go back to the source</strong>
            <p>Inspect where each assertion came from.</p>
          </div>
        </li>
      </ol>
      <p className="research-entry-disclaimer">No connections are inferred from matching names.</p>
    </aside>
  );
}
