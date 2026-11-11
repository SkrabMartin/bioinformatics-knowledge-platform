import type { Disease, ProvenanceFields } from "./entities";

export interface Phenotype extends ProvenanceFields {
  id: number;
  hpo_id: string;
  name: string;
  description: string | null;
  source_release: string;
}

export interface DiseasePhenotype extends ProvenanceFields {
  id: number;
  disease_id: number;
  phenotype_id: number;
  qualifier: "present" | "excluded";
  evidence_kind: "curated" | "structured_metadata";
  evidence_code: string | null;
  reference: string;
  source_release: string;
  phenotype: Phenotype;
  disease: Disease;
}
