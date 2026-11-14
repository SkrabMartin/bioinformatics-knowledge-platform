import { useState } from "react";
import { Link } from "react-router-dom";
import { useEntity } from "../hooks/useEntity";
import { ErrorState, LoadingState } from "./States";
import { ProvenanceBadge } from "./ProvenanceBadge";

type NameKind = "gene" | "protein" | "organism" | "publication";
type Hints = {
  query: string;
  items: {
    entity_type: NameKind;
    entity_id: number;
    label: string;
    matched_name: string;
    match_field: string;
    source: string;
    href: string | null;
    similarity: number;
  }[];
};
function RequestedNames({ query, kind }: { query: string; kind: NameKind | null }) {
  const params = new URLSearchParams({ q: query, limit: "6" });
  if (kind) params.set("type", kind);
  const { data, loading, error, retry } = useEntity<Hints>(`search/name-suggestions?${params}`);
  if (loading) return <LoadingState label="Looking for similar stored names" />;
  if (error) return <ErrorState message={error} onRetry={retry} />;
  if (!data) return null;
  return (
    <>
      {data.items.length === 0 ? (
        <p>No similar stored names met the text threshold.</p>
      ) : (
        <ul className="related-list">
          {data.items.map((item) => (
            <li key={`${item.entity_type}:${item.entity_id}`}>
              {item.href ? <Link to={item.href}>{item.label}</Link> : <strong>{item.label}</strong>}
              <p>
                {item.entity_type} · {item.match_field.replaceAll("_", " ")}: {item.matched_name}
              </p>
              <p>
                Text similarity score: <span className="mono">{item.similarity.toFixed(2)}</span> ·{" "}
                <ProvenanceBadge source={item.source} />
              </p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
export function SimilarNames({ query, category }: { query: string; category: string | null }) {
  const [requested, setRequested] = useState(false);
  const supported =
    category === null || ["gene", "protein", "organism", "publication"].includes(category);
  const normalized = query.normalize("NFC").trim().replace(/\s+/g, " ");
  const eligible =
    normalized.length >= 4 &&
    normalized.length <= 120 &&
    /^[\p{L} '-]+$/u.test(normalized) &&
    normalized.split(" ").some((word) => word.length >= 4) &&
    !(normalized.split(" ").length === 1 && normalized === normalized.toLocaleUpperCase());
  if (!supported || !eligible) return null;
  return (
    <section className="search-intro" aria-label="Similar stored names">
      <h2>Similar stored names</h2>
      <p className="context-note">
        Optional text hints for gene/protein names, organism names and publication titles. These are
        not identifier corrections, biological relationships or confidence estimates. Normal search
        results and counts stay unchanged.
      </p>
      {!requested ? (
        <button type="button" onClick={() => setRequested(true)}>
          Find similar names
        </button>
      ) : (
        <RequestedNames query={normalized} kind={category as NameKind | null} />
      )}
    </section>
  );
}
