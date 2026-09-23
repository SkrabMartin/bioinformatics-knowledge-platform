import { Link } from "react-router-dom";

import type { ReactNode } from "react";

import type { SearchResult } from "../types/entities";
import { ProvenanceBadge } from "./ProvenanceBadge";

const entityLabels = {
  gene: "Gene",
  protein: "Protein",
  organism: "Organism",
};

const fieldLabels: Record<string, string> = {
  accession: "Accession",
  common_name: "Common name",
  description: "Description",
  ensembl_gene_id: "Ensembl Gene ID",
  function: "Function",
  gene_symbol: "Encoding gene",
  name: "Name",
  ncbi_gene_id: "NCBI Gene ID",
  scientific_name: "Scientific name",
  symbol: "Symbol",
  taxonomy_id: "Taxonomy ID",
};

export function SearchResultCard({ result, query }: { result: SearchResult; query: string }) {
  const title = <HighlightedText text={result.primary_label} query={query} />;
  return (
    <article className="search-result-card">
      <div className="result-card-heading">
        <span className={`entity-type entity-type--${result.entity_type}`}>
          {entityLabels[result.entity_type]}
        </span>
        <ProvenanceBadge source={result.source} />
      </div>
      <h3>{result.href ? <Link to={result.href}>{title}</Link> : title}</h3>
      {result.secondary_label && (
        <p className="result-secondary">
          <HighlightedText text={result.secondary_label} query={query} />
        </p>
      )}
      {result.organism && (
        <p className="result-organism">
          <i>{result.organism.scientific_name}</i>
          {result.organism.taxonomy_id && <span>Taxonomy {result.organism.taxonomy_id}</span>}
        </p>
      )}
      {result.description && (
        <p className="result-description">
          <HighlightedText text={result.description} query={query} />
        </p>
      )}
      {result.matched_fields.length > 0 && (
        <dl className="match-list">
          {result.matched_fields.slice(0, 3).map((match) => (
            <div key={`${match.field}-${match.value}`}>
              <dt>{fieldLabels[match.field] ?? match.field}</dt>
              <dd>
                <HighlightedText text={match.value} query={query} />
              </dd>
            </div>
          ))}
        </dl>
      )}
    </article>
  );
}

export function HighlightedText({ text, query }: { text: string; query: string }) {
  const terms = Array.from(new Set(query.match(/[\p{L}\p{N}_.:-]+/gu)?.filter(Boolean) ?? [])).sort(
    (left, right) => right.length - left.length,
  );
  if (!terms.length) return text;
  const expression = new RegExp(`(${terms.map(escapeRegularExpression).join("|")})`, "giu");
  const parts = text.split(expression);
  return parts.map((part, index): ReactNode =>
    terms.some((term) => term.toLocaleLowerCase() === part.toLocaleLowerCase()) ? (
      <mark key={`${part}-${index}`}>{part}</mark>
    ) : (
      part
    ),
  );
}

function escapeRegularExpression(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
