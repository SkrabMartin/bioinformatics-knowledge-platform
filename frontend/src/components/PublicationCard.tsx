import { Link } from "react-router-dom";

import type { Publication } from "../types/entities";
import { ProvenanceBadge } from "./ProvenanceBadge";

export function CitationLinks({ publication }: { publication: Publication }) {
  return (
    <div className="citation-links">
      {publication.pubmed_id && (
        <a
          href={`https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(publication.pubmed_id)}/`}
          target="_blank"
          rel="noreferrer"
        >
          PubMed {publication.pubmed_id} ↗
        </a>
      )}
      {publication.doi && (
        <a
          href={`https://doi.org/${encodeURIComponent(publication.doi)}`}
          target="_blank"
          rel="noreferrer"
        >
          DOI: {publication.doi} ↗
        </a>
      )}
    </div>
  );
}

export function PublicationCard({ publication }: { publication: Publication }) {
  return (
    <article className="publication-card">
      <div className="result-card-heading">
        <span className="entity-type">Publication</span>
        <ProvenanceBadge source={publication.source} />
      </div>
      <h3>
        <Link to={`/publication/${publication.id}`}>{publication.title}</Link>
      </h3>
      <p>
        {publication.authors.slice(0, 5).join("; ") || "Authors not supplied"}
        {publication.authors.length > 5 && "; et al."}
      </p>
      <p className="context-note">
        {publication.journal ?? "Journal not supplied"} ·{" "}
        {publication.publication_date ?? "Date not supplied"}
      </p>
      <CitationLinks publication={publication} />
    </article>
  );
}
