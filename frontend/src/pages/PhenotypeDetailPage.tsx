import { useParams } from "react-router-dom";
import { DetailHeader, DetailSection, FactGrid, ProvenancePanel } from "../components/EntityDetail";
import { PhenotypeAnnotations } from "../components/PhenotypeAnnotations";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Phenotype } from "../types/phenotypes";

export function PhenotypeDetailPage() {
  const { id } = useParams();
  const { data, loading, error, retry } = useEntity<Phenotype>(id ? `phenotypes/${id}` : null);
  if (loading)
    return (
      <div className="page-container">
        <LoadingState label="Loading phenotype" />
      </div>
    );
  if (error)
    return (
      <div className="page-container">
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  if (!data) return null;
  return (
    <article className="detail-page">
      <DetailHeader
        type="Phenotype"
        title={data.name}
        subtitle={data.hpo_id}
        organism="HPO-identified term"
        monoSubtitle
      />
      <div className="detail-content">
        <DetailSection title="Overview">
          <p>{data.description ?? "No description was supplied by the source."}</p>
          <FactGrid
            facts={[
              { label: "HPO ID", value: data.hpo_id },
              { label: "Source release", value: data.source_release },
            ]}
          />
        </DetailSection>
        <DetailSection title="Disease annotations">
          <PhenotypeAnnotations key={data.id} kind="phenotype" id={data.id} />
        </DetailSection>
        <DetailSection title="Source provenance">
          <ProvenancePanel record={data} />
        </DetailSection>
      </div>
    </article>
  );
}
