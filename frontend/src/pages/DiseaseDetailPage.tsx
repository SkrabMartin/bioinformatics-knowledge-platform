import { useParams } from "react-router-dom";

import { DetailHeader, DetailSection, FactGrid, ProvenancePanel } from "../components/EntityDetail";
import { RelationshipPanel } from "../components/RelationshipPanel";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Disease } from "../types/entities";

export function DiseaseDetailPage() {
  const { id } = useParams();
  const { data: disease, error, loading, retry } = useEntity<Disease>(id ? `diseases/${id}` : null);

  if (loading)
    return (
      <div className="page-container">
        <LoadingState label="Loading disease record" />
      </div>
    );
  if (error)
    return (
      <div className="page-container">
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  if (!disease) return null;

  return (
    <article className="detail-page">
      <DetailHeader
        type="Disease"
        title={disease.name}
        subtitle={disease.mondo_id ?? disease.disease_ontology_id ?? "No ontology ID stored"}
        organism="No organism scope stored"
      />
      <div className="detail-content">
        <DetailSection title="Overview">
          <p className="long-form">
            {disease.description ?? "No description was supplied by the source."}
          </p>
        </DetailSection>
        <DetailSection title="Identifiers">
          <FactGrid
            facts={[
              { label: "MONDO ID", value: disease.mondo_id },
              { label: "Disease Ontology ID", value: disease.disease_ontology_id },
            ]}
          />
        </DetailSection>
        <RelationshipPanel key={disease.id} entityType="disease" entityId={disease.id} />
        <DetailSection title="Source provenance">
          <ProvenancePanel record={disease} />
        </DetailSection>
      </div>
    </article>
  );
}
