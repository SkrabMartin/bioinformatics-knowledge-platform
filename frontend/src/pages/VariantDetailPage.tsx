import { useParams } from "react-router-dom";

import { DetailHeader, DetailSection, FactGrid, ProvenancePanel } from "../components/EntityDetail";
import { RelationshipPanel } from "../components/RelationshipPanel";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Variant } from "../types/entities";

export function VariantDetailPage() {
  const { id } = useParams();
  const { data: variant, error, loading, retry } = useEntity<Variant>(id ? `variants/${id}` : null);

  if (loading)
    return (
      <div className="page-container">
        <LoadingState label="Loading variant record" />
      </div>
    );
  if (error)
    return (
      <div className="page-container">
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  if (!variant) return null;

  return (
    <article className="detail-page">
      <DetailHeader
        type="Variant"
        title={variant.rsid ?? variant.hgvs ?? String(variant.id)}
        subtitle={variant.hgvs && variant.rsid ? variant.hgvs : "Sourced variant record"}
        organism={variant.organism.scientific_name}
      />
      <div className="detail-content">
        <DetailSection title="Overview">
          <p className="long-form">
            {variant.description ?? "No description was supplied by the source."}
          </p>
        </DetailSection>
        <DetailSection title="Identifiers">
          <FactGrid
            facts={[
              { label: "dbSNP rsID", value: variant.rsid },
              { label: "HGVS expression", value: variant.hgvs },
              { label: "NCBI taxonomy ID", value: variant.organism.taxonomy_id },
            ]}
          />
        </DetailSection>
        <RelationshipPanel key={variant.id} entityType="variant" entityId={variant.id} />
        <DetailSection title="Source provenance">
          <ProvenancePanel record={variant} />
        </DetailSection>
      </div>
    </article>
  );
}
