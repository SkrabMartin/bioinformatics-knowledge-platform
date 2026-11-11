import { useState } from "react";
import { Link } from "react-router-dom";
import { useEntity } from "../hooks/useEntity";
import type { Page } from "../types/entities";
import type { DiseasePhenotype } from "../types/phenotypes";
import { ProvenancePanel } from "./EntityDetail";
import { Pagination } from "./Pagination";
import { ErrorState, LoadingState } from "./States";

export function PhenotypeAnnotations({ kind, id }: { kind: "disease" | "phenotype"; id: number }) {
  const [page, setPage] = useState(1);
  const resource = kind === "disease" ? `diseases/${id}/phenotypes` : `phenotypes/${id}/diseases`;
  const { data, loading, error, retry } = useEntity<Page<DiseasePhenotype>>(
    `${resource}?page=${page}&page_size=10`,
  );
  return (
    <>
      <p className="context-note">
        These are source assertions about diseases. Present and excluded annotations remain
        distinct; absence of an annotation does not imply either state. Sources may disagree.
      </p>
      {loading && <LoadingState label="Loading phenotype annotations" />}
      {error && <ErrorState message={error} onRetry={retry} />}
      {!loading && !error && data && (
        <>
          {!data.items.length && (
            <p className="empty-inline">
              No sourced disease–phenotype annotations have been stored for this record.
            </p>
          )}
          <ul className="related-list">
            {data.items.map((record) => (
              <li key={record.id}>
                <strong>
                  {record.qualifier === "excluded"
                    ? "Excluded phenotype (source assertion)"
                    : "Present phenotype (source assertion)"}
                </strong>
                {kind === "disease" ? (
                  <Link to={`/phenotype/${record.phenotype.id}`}>
                    {record.phenotype.hpo_id} · {record.phenotype.name}
                  </Link>
                ) : (
                  <Link to={`/disease/${record.disease.id}`}>{record.disease.name}</Link>
                )}
                <p>
                  Evidence: {record.evidence_kind}
                  {record.evidence_code ? ` · ${record.evidence_code}` : ""} · Reference:{" "}
                  {record.reference} · Release: {record.source_release}
                </p>
                <ProvenancePanel record={record} />
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
    </>
  );
}
