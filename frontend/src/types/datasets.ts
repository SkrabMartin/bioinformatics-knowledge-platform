import type { ProvenanceFields } from "./entities";

export interface Dataset extends ProvenanceFields {
  id: number;
  repository: "GEO";
  accession: string;
  title: string;
  description: string | null;
  experiment_types: string[];
  organism_names: string[];
  taxonomy_ids: string[];
  platform_accessions: string[];
  publication_pmids: string[];
  sample_count: number | null;
  source_updated_date: string;
}
