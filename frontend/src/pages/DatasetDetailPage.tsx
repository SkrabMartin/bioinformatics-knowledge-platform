import { useParams } from "react-router-dom";
import { DetailHeader, DetailSection, FactGrid, ProvenancePanel } from "../components/EntityDetail";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import type { Dataset } from "../types/datasets";

export function DatasetDetailPage() {
  const { id } = useParams();
  const { data, loading, error, retry } = useEntity<Dataset>(id ? `datasets/${id}` : null);
  if (loading)
    return (
      <div className="page-container">
        <LoadingState label="Loading dataset" />
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
        type="Dataset"
        title={data.title}
        subtitle={`${data.repository} · ${data.accession}`}
        organism={data.organism_names.join("; ") || "Organism metadata not supplied"}
      />
      <div className="detail-content">
        <DetailSection title="Repository metadata">
          <FactGrid
            facts={[
              { label: "Experiment types", value: data.experiment_types.join("; ") || null },
              { label: "Reported taxonomy IDs", value: data.taxonomy_ids.join(", ") || null },
              { label: "Platforms", value: data.platform_accessions.join(", ") || null },
              { label: "Repository sample records", value: data.sample_count },
              { label: "Source record updated", value: data.source_updated_date },
            ]}
          />
          <p className="context-note">
            Sample counts describe repository sample records, not necessarily patients, independent
            subjects or analysis-ready observations. Organism labels and taxonomy IDs are source
            metadata, not inferred entity mappings.
          </p>
        </DetailSection>
        <DetailSection title="Source summary">
          <p className="long-form">{data.description ?? "No source summary was supplied."}</p>
        </DetailSection>
        <DetailSection title="Source-reported publications">
          {data.publication_pmids.length ? (
            <ul>
              {data.publication_pmids.map((pmid) => (
                <li key={pmid}>
                  <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}/`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    PubMed {pmid}
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p>No publication references are stored.</p>
          )}
          <p className="context-note">
            These are repository-supplied external references. They do not imply that the citation
            has been imported locally.
          </p>
        </DetailSection>
        <DetailSection title="Data access">
          <a href={data.source_url ?? undefined} target="_blank" rel="noreferrer">
            Open GEO record for files and access information
          </a>
          <p className="context-note">
            BKP stores discovery metadata only. Experimental matrices and raw files are not
            downloaded or analyzed here. Tissue, disease and clinical conclusions are not inferred
            from the study title.
          </p>
        </DetailSection>
        <DetailSection title="Source provenance">
          <ProvenancePanel record={data} />
        </DetailSection>
      </div>
    </article>
  );
}
