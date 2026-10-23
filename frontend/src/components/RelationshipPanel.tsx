import { useState } from "react";
import { Link } from "react-router-dom";

import { useRelationships } from "../hooks/useRelationships";
import type { RelatedEntityType } from "../types/entities";
import { DetailSection } from "./EntityDetail";
import { Pagination } from "./Pagination";
import { ProvenanceBadge } from "./ProvenanceBadge";
import { ErrorState, LoadingState } from "./States";

const predicateLabels = {
  associated_with: "associated with",
  located_in: "located in",
  interacts_with: "interacts with",
  encodes: "encodes",
  mentions: "mentions (source link)",
  studies: "studies (source assertion)",
  discusses: "discusses (source assertion)",
};

export function RelationshipPanel({
  entityType,
  entityId,
}: {
  entityType: RelatedEntityType;
  entityId: number;
}) {
  const [page, setPage] = useState(1);
  const { data, error, loading, retry } = useRelationships(entityType, entityId, page);

  return (
    <DetailSection title="Relationships">
      <p>
        <Link className="button button--small" to={`/graph?type=${entityType}&id=${entityId}`}>
          Explore graph ↗
        </Link>
      </p>
      <div className="relationship-panel" aria-live="polite">
        {loading && <LoadingState label="Loading sourced relationships" />}
        {!loading && error && <ErrorState message={error} onRetry={retry} />}
        {!loading && !error && data?.items.length === 0 && (
          <p className="context-note">No sourced relationships are stored for this record.</p>
        )}
        {!loading && !error && data && data.items.length > 0 && (
          <>
            <ul className="relationship-list">
              {data.items.map((relationship) => (
                <li
                  key={`${relationship.relationship_type}-${relationship.relationship_id}`}
                  className="relationship-card"
                >
                  <p className="relationship-statement">
                    <Link to={relationship.subject.href}>{relationship.subject.label}</Link>
                    <span>{predicateLabels[relationship.predicate]}</span>
                    <Link to={relationship.object.href}>{relationship.object.label}</Link>
                  </p>
                  <div className="relationship-meta">
                    <ProvenanceBadge source={relationship.source} />
                    <span>Source ID: {relationship.source_identifier ?? "Not supplied"}</span>
                    {relationship.evidence_kind && (
                      <span>
                        {relationship.evidence_kind === "curated"
                          ? "Curated assertion"
                          : "Structured provider metadata"}
                      </span>
                    )}
                    {relationship.provenance_basis === "protein_record" && (
                      <span>Link inherited from protein record</span>
                    )}
                  </div>
                  {relationship.evidence_text && <p>{relationship.evidence_text}</p>}
                  {relationship.source_url && (
                    <a href={relationship.source_url} target="_blank" rel="noreferrer">
                      View source <span aria-hidden="true">↗</span>
                    </a>
                  )}
                </li>
              ))}
            </ul>
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              onPageChange={setPage}
            />
          </>
        )}
      </div>
    </DetailSection>
  );
}
