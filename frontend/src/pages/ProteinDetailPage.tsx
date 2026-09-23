import { Link, useParams } from "react-router-dom";
import type { ReactNode } from "react";

import { DetailHeader, DetailSection, FactGrid, ProvenancePanel } from "../components/EntityDetail";
import { RelationshipPanel } from "../components/RelationshipPanel";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Protein } from "../types/entities";

export function ProteinDetailPage() {
  const { accession } = useParams();
  const resource = accession ? `proteins/by-accession/${encodeURIComponent(accession)}` : null;
  const { data: protein, error, loading, retry } = useEntity<Protein>(resource);

  if (loading)
    return (
      <DetailState>
        <LoadingState label="Loading protein record" />
      </DetailState>
    );
  if (error)
    return (
      <DetailState>
        <ErrorState message={error} onRetry={retry} />
      </DetailState>
    );
  if (!protein) return null;

  return (
    <article className="detail-page">
      <DetailHeader
        type="Protein"
        title={protein.accession}
        subtitle={protein.name}
        organism={protein.organism.scientific_name}
      />
      <div className="detail-content">
        <DetailSection title="Overview">
          <p className="long-form">
            {protein.function ?? "No function statement was supplied by the source."}
          </p>
        </DetailSection>
        <DetailSection title="Record details">
          <FactGrid
            facts={[
              { label: "UniProt accession", value: protein.accession },
              {
                label: "Sequence length",
                value: protein.sequence_length ? `${protein.sequence_length} amino acids` : null,
              },
              { label: "NCBI taxonomy ID", value: protein.organism.taxonomy_id },
            ]}
          />
        </DetailSection>
        <DetailSection title="Encoded by">
          {protein.gene ? (
            <Link
              className="linked-entity"
              to={`/gene/${encodeURIComponent(protein.gene.symbol)}?taxonomy_id=${encodeURIComponent(protein.organism.taxonomy_id ?? "9606")}`}
            >
              <strong>{protein.gene.symbol}</strong>
              <span>{protein.gene.name}</span>
            </Link>
          ) : (
            <p className="context-note">
              This protein is not linked to a gene in the local database. Import the gene first,
              then re-import this accession.
            </p>
          )}
        </DetailSection>
        <RelationshipPanel key={protein.id} entityType="protein" entityId={protein.id} />
        <DetailSection title="Source provenance">
          <ProvenancePanel record={protein} />
        </DetailSection>
      </div>
    </article>
  );
}

function DetailState({ children }: { children: ReactNode }) {
  return <div className="page-container detail-state">{children}</div>;
}
