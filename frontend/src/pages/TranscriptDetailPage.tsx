import { Link, useParams } from "react-router-dom";
import { DetailHeader, DetailSection, FactGrid, ProvenancePanel } from "../components/EntityDetail";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Transcript } from "../types/entities";

export function TranscriptDetailPage() {
  const { accession } = useParams();
  const { data, loading, error, retry } = useEntity<Transcript>(
    accession ? "transcripts/by-ensembl/" + encodeURIComponent(accession) : null,
  );
  if (loading)
    return (
      <div className="page-container">
        <LoadingState label="Loading transcript" />
      </div>
    );
  if (error)
    return (
      <div className="page-container">
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  if (!data) return null;
  const taxonomy = data.gene.organism.taxonomy_id;
  return (
    <article className="detail-page">
      <DetailHeader
        type="Transcript"
        title={data.ensembl_transcript_id}
        subtitle={data.name ?? "No display name supplied by source"}
        organism={data.gene.organism.scientific_name}
        mono
      />
      <div className="detail-content">
        <DetailSection title="Annotation context">
          <FactGrid
            facts={[
              { label: "Transcript version", value: data.version },
              { label: "Biotype", value: data.biotype },
              { label: "Assembly name", value: data.assembly_name },
              { label: "Reference region", value: data.sequence_region },
              {
                label: "Coordinates",
                value:
                  data.start_position.toLocaleString() + "–" + data.end_position.toLocaleString(),
              },
              { label: "Strand", value: data.strand },
              { label: "Ensembl data release", value: data.source_release },
            ]}
          />
          <p className="context-note">
            Coordinates are one-based and inclusive within the named assembly and region. Sequence,
            exon structure and protein translation are not inferred.
          </p>
        </DetailSection>
        <DetailSection title="Source-reported parent gene">
          {taxonomy ? (
            <Link
              to={
                "/gene/" +
                encodeURIComponent(data.gene.symbol) +
                "?taxonomy_id=" +
                encodeURIComponent(taxonomy)
              }
            >
              {data.gene.symbol}
            </Link>
          ) : (
            <span>{data.gene.symbol}</span>
          )}
          <p className="context-note">
            This retained annotation is not a claim about a current canonical isoform.
          </p>
        </DetailSection>
        <DetailSection title="Source provenance">
          <ProvenancePanel record={data} />
        </DetailSection>
      </div>
    </article>
  );
}
