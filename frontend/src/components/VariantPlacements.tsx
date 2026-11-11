import { useState } from "react";
import { useEntity } from "../hooks/useEntity";
import type { Page, ProvenanceFields } from "../types/entities";
import { FactGrid, ProvenancePanel } from "./EntityDetail";
import { Pagination } from "./Pagination";
import { ErrorState, LoadingState } from "./States";

interface Placement extends ProvenanceFields {
  id: number;
  variant_id: number;
  assembly_name: string;
  assembly_accession: string | null;
  sequence_accession: string;
  sequence_region: string | null;
  taxonomy_id: string;
  coordinate_system: "one_based_closed";
  strand: "+";
  start_position: number;
  end_position: number;
  reference_allele: string;
  alternate_allele: string;
  source_release: string;
}

export function VariantPlacements({ variantId }: { variantId: number }) {
  const [page, setPage] = useState(1);
  const { data, loading, error, retry } = useEntity<Page<Placement>>(
    `variants/${variantId}/placements?page=${page}&page_size=10`,
  );
  return (
    <>
      <p className="context-note">
        Source-provided literal sequence replacements, on the forward reference strand. Coordinates
        are 1-based and closed, including any reference padding. Reference bases and sequence
        membership in the assembly are not independently verified here. No clinical significance is
        inferred.
      </p>
      {loading && <LoadingState label="Loading genomic placements" />}
      {error && <ErrorState message={error} onRetry={retry} />}
      {!loading && !error && data && (
        <>
          {!data.items.length && (
            <p className="empty-inline">
              No sourced genomic placements have been stored for this variant. An rsID or HGVS label
              alone does not establish an assembly or genomic position.
            </p>
          )}
          <ul className="related-list">
            {data.items.map((record) => (
              <li key={record.id}>
                <h3>
                  {record.assembly_name} · {record.sequence_accession}:{record.start_position}–
                  {record.end_position}
                </h3>
                <FactGrid
                  facts={[
                    { label: "Assembly accession", value: record.assembly_accession },
                    { label: "Source sequence region", value: record.sequence_region },
                    { label: "Coordinates", value: "1-based closed · forward (+) strand" },
                    { label: "Taxonomy ID", value: record.taxonomy_id },
                    { label: "Source release", value: record.source_release },
                  ]}
                />
                <p>
                  REF:{" "}
                  <code className="long-form" style={{ overflowWrap: "anywhere" }}>
                    {record.reference_allele}
                  </code>
                </p>
                <p>
                  ALT:{" "}
                  <code className="long-form" style={{ overflowWrap: "anywhere" }}>
                    {record.alternate_allele}
                  </code>
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
