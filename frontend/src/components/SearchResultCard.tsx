import { Link } from "react-router-dom";

import type { ReactNode } from "react";

import type { SearchResult } from "../types/entities";
import { ProvenanceBadge } from "./ProvenanceBadge";

const entityLabels = {
  dataset: "Dataset",
  phenotype: "Phenotype",
  gene: "Gene",
  protein: "Protein",
  organism: "Organism",
  publication: "Publication",
  transcript: "Transcript",
  disease: "Disease",
  variant: "Variant",
  pathway: "Pathway",
  biological_process: "Biological process",
  molecular_function: "Molecular function",
  cellular_component: "Cellular component",
};

const fieldLabels: Record<string, string> = {
  hpo_id: "HPO ID",
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
  pubmed_id: "PMID",
  doi: "DOI",
  title: "Title",
  journal: "Journal",
  abstract: "Abstract",
  keywords: "Source keywords",
  transcript_identifier: "Transcript identifier",
  biotype: "Biotype",
  assembly: "Assembly",
  mondo_id: "MONDO ID",
  disease_ontology_id: "Disease Ontology ID",
  rsid: "rsID",
  hgvs: "HGVS",
  source_identifier: "Source identifier",
  go_id: "GO ID",
};

/** Matched fields and record types whose values are identifiers, shown in monospace. */
const identifierFields = new Set([
  "hpo_id",
  "accession",
  "ensembl_gene_id",
  "ncbi_gene_id",
  "taxonomy_id",
  "pubmed_id",
  "doi",
  "transcript_identifier",
  "mondo_id",
  "disease_ontology_id",
  "rsid",
  "hgvs",
  "source_identifier",
  "go_id",
]);
const identifierTitled = new Set(["variant", "transcript", "protein"]);

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
      <h3 className={identifierTitled.has(result.entity_type) ? "mono" : undefined}>
        {result.href ? <Link to={result.href}>{title}</Link> : title}
      </h3>
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
              <dd className={identifierFields.has(match.field) ? "mono" : undefined}>
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
