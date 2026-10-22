import { useParams } from "react-router-dom";

import { DetailHeader, DetailSection, FactGrid, ProvenancePanel } from "../components/EntityDetail";
import { CitationLinks } from "../components/PublicationCard";
import { RelationshipPanel } from "../components/RelationshipPanel";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Publication } from "../types/entities";

export function PublicationDetailPage() {
  const { id } = useParams();
  const { data, loading, error, retry } = useEntity<Publication>(
    id ? `publications/${encodeURIComponent(id)}` : null,
  );
  if (loading)
    return (
      <div className="page-container">
        <LoadingState label="Loading publication" />
      </div>
    );
  if (error)
    return (
      <div className="page-container">
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  if (!data) return null;
  const precision =
    data.publication_date?.length === 4
      ? "Year only"
      : data.publication_date?.length === 7
        ? "Month precision"
        : data.publication_date
          ? "Day precision"
          : "Not supplied";
  return (
    <article className="detail-page">
      <DetailHeader
        type="Publication"
        title={data.title}
        subtitle={data.journal ?? "Journal not supplied"}
      />
      <div className="detail-content">
        <DetailSection title="Citation">
          <FactGrid
            facts={[
              { label: "PMID", value: data.pubmed_id },
              { label: "DOI", value: data.doi },
              { label: "Publication date", value: data.publication_date },
              { label: "Date precision", value: precision },
              { label: "Source date text", value: data.publication_date_text },
            ]}
          />
          <CitationLinks publication={data} />
        </DetailSection>
        <DetailSection title="Authors">
          <p className="long-form">
            {data.authors.join("; ") || "No author names supplied by the source."}
          </p>
        </DetailSection>
        <DetailSection title="Abstract">
          <p className="long-form publication-abstract">
            {data.abstract ?? "No abstract was supplied by the source."}
          </p>
        </DetailSection>
        <p className="context-note">
          Literature links are source assertions. A mention does not establish a causal or clinical
          relationship.
        </p>
        <RelationshipPanel key={data.id} entityType="publication" entityId={data.id} />
        <DetailSection title="Source provenance">
          <ProvenancePanel record={data} />
        </DetailSection>
      </div>
    </article>
  );
}
