import { Link, useParams, useSearchParams } from "react-router-dom";
import type { ReactNode } from "react";

import { DetailHeader, DetailSection, FactGrid, ProvenancePanel } from "../components/EntityDetail";
import { RelationshipPanel } from "../components/RelationshipPanel";
import { PublicationPanel } from "../components/PublicationPanel";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { GeneDetail } from "../types/entities";

export function GeneDetailPage() {
  const { symbol } = useParams();
  const [params] = useSearchParams();
  const taxonomyId = params.get("taxonomy_id") ?? "9606";
  const resource = symbol
    ? `genes/by-symbol/${encodeURIComponent(symbol)}?taxonomy_id=${encodeURIComponent(taxonomyId)}`
    : null;
  const { data: gene, error, loading, retry } = useEntity<GeneDetail>(resource);

  if (loading)
    return (
      <DetailState>
        <LoadingState label="Loading gene record" />
      </DetailState>
    );
  if (error)
    return (
      <DetailState>
        <ErrorState message={error} onRetry={retry} />
      </DetailState>
    );
  if (!gene) return null;

  const location = gene.chromosome ? `Chromosome ${gene.chromosome}` : "Not available";
  const coordinates =
    gene.start_position && gene.end_position
      ? `${gene.start_position.toLocaleString()}–${gene.end_position.toLocaleString()}`
      : "Not available";

  return (
    <article className="detail-page">
      <DetailHeader
        type="Gene"
        title={gene.symbol}
        subtitle={gene.name}
        organism={gene.organism.scientific_name}
      />
      <div className="detail-content">
        <DetailSection title="Overview">
          <p className="long-form">
            {gene.description ?? "No description was supplied by the source."}
          </p>
        </DetailSection>
        <DetailSection title="Identifiers">
          <FactGrid
            facts={[
              { label: "NCBI Gene ID", value: gene.ncbi_gene_id },
              { label: "Ensembl Gene ID", value: gene.ensembl_gene_id },
              { label: "NCBI taxonomy ID", value: gene.organism.taxonomy_id },
            ]}
          />
        </DetailSection>
        <DetailSection title="Genomic location">
          <FactGrid
            facts={[
              { label: "Location", value: location },
              { label: "Coordinates", value: coordinates },
              { label: "Strand", value: gene.strand },
            ]}
          />
          <p className="context-note">
            Coordinates are one-based and inclusive. Assembly metadata is not yet stored.
          </p>
        </DetailSection>
        <DetailSection title="Associated proteins">
          {gene.proteins.length ? (
            <ul className="related-list">
              {gene.proteins.map((protein) => (
                <li key={protein.id}>
                  <Link to={`/protein/${encodeURIComponent(protein.accession)}`}>
                    <strong>{protein.accession}</strong>
                    <span>{protein.name}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="context-note">No protein has been linked in the local database.</p>
          )}
        </DetailSection>
        <RelationshipPanel key={gene.id} entityType="gene" entityId={gene.id} />
        <PublicationPanel key={`publications-${gene.id}`} geneId={gene.id} />
        <DetailSection title="Source provenance">
          <ProvenancePanel record={gene} />
        </DetailSection>
      </div>
    </article>
  );
}

function DetailState({ children }: { children: ReactNode }) {
  return <div className="page-container detail-state">{children}</div>;
}
