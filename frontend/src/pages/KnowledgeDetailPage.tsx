import { useParams } from "react-router-dom";
import { DetailHeader, DetailSection, FactGrid, ProvenancePanel } from "../components/EntityDetail";
import { KnowledgeNavigation } from "../components/KnowledgeNavigation";
import { RelationshipPanel } from "../components/RelationshipPanel";
import { ErrorState, LoadingState } from "../components/States";
import { knowledgeCollections } from "../features/knowledge/config";
import { useEntity } from "../hooks/useEntity";
import type { KnowledgeKind, OntologyTerm, Pathway } from "../types/entities";

export function KnowledgeDetailPage({ kind }: { kind: KnowledgeKind }) {
  const { id } = useParams();
  const collection = knowledgeCollections[kind];
  const {
    data: record,
    loading,
    error,
    retry,
  } = useEntity<OntologyTerm | Pathway>(id ? `${collection.resource}/${id}` : null);
  if (loading)
    return (
      <div className="page-container">
        <LoadingState label="Loading functional knowledge record" />
      </div>
    );
  if (error)
    return (
      <div className="page-container">
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  if (!record) return null;
  return (
    <article className="detail-page">
      <DetailHeader
        type={collection.singular}
        title={record.name}
        subtitle={"go_id" in record ? record.go_id : (record.source_identifier ?? "Source record")}
        organism={
          "organism_id" in record && record.organism_id
            ? `Organism record #${record.organism_id}`
            : "No organism scope supplied"
        }
      />
      <div className="detail-content">
        <KnowledgeNavigation />
        <DetailSection title="Overview">
          <p className="long-form">{record.description ?? "No source description supplied."}</p>
        </DetailSection>
        <DetailSection title="Identity and release">
          <FactGrid
            facts={[
              { label: "Source identifier", value: record.source_identifier },
              { label: "Source release", value: record.source_release },
              {
                label: "GO aspect",
                value: "kind" in record ? record.kind.replaceAll("_", " ") : "Not a GO term",
              },
            ]}
          />
        </DetailSection>
        {kind !== "pathway" && (
          <DetailSection title="Ontology context">
            <p className="long-form">
              The Relationships section lists direct annotations and direct is_a parents or
              children. A term may have multiple parents. The graph follows stored edges; it does
              not automatically propagate annotations to ancestors.
            </p>
          </DetailSection>
        )}
        <RelationshipPanel key={`${kind}:${record.id}`} entityType={kind} entityId={record.id} />
        <DetailSection title="Source provenance">
          <ProvenancePanel record={record} />
        </DetailSection>
      </div>
    </article>
  );
}
