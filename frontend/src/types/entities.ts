export interface ProvenanceFields {
  source: string;
  source_identifier: string | null;
  source_url: string | null;
  imported_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrganismSummary {
  id: number;
  scientific_name: string;
  common_name: string | null;
  taxonomy_id: string | null;
}

export interface Organism extends OrganismSummary, ProvenanceFields {}

export interface Gene extends ProvenanceFields {
  id: number;
  symbol: string;
  name: string;
  description: string | null;
  organism_id: number;
  organism: OrganismSummary;
  chromosome: string | null;
  start_position: number | null;
  end_position: number | null;
  strand: "+" | "-" | null;
  ncbi_gene_id: string | null;
  ensembl_gene_id: string | null;
}

export interface GeneSummary {
  id: number;
  symbol: string;
  name: string;
}

export interface ProteinSummary {
  id: number;
  accession: string;
  name: string;
}

export interface GeneDetail extends Gene {
  proteins: ProteinSummary[];
}

export interface Protein extends ProvenanceFields {
  id: number;
  accession: string;
  name: string;
  gene_id: number | null;
  gene: GeneSummary | null;
  organism_id: number;
  organism: OrganismSummary;
  function: string | null;
  sequence_length: number | null;
}

export interface Disease extends ProvenanceFields {
  id: number;
  name: string;
  description: string | null;
  mondo_id: string | null;
  disease_ontology_id: string | null;
}

export interface Variant extends ProvenanceFields {
  id: number;
  rsid: string | null;
  hgvs: string | null;
  description: string | null;
  organism_id: number;
  organism: OrganismSummary;
}

export type RelatedEntityType =
  | "gene"
  | "protein"
  | "variant"
  | "disease"
  | "publication"
  | "pathway"
  | "biological_process"
  | "molecular_function";

export type KnowledgeKind = "pathway" | "biological_process" | "molecular_function";
export interface Pathway extends ProvenanceFields {
  id: number;
  name: string;
  description: string | null;
  organism_id: number | null;
  source_release: string;
}
export interface OntologyTerm extends ProvenanceFields {
  id: number;
  name: string;
  description: string | null;
  kind: "biological_process" | "molecular_function";
  go_id: string;
  source_release: string;
}

export interface Publication extends ProvenanceFields {
  id: number;
  pubmed_id: string | null;
  doi: string | null;
  title: string;
  abstract: string | null;
  journal: string | null;
  authors: string[];
  publication_date: string | null;
  publication_date_text: string | null;
}

export interface RelationshipNode {
  entity_type: RelatedEntityType;
  entity_id: number;
  label: string;
  href: string;
}

export interface EntityRelationship {
  relationship_type:
    | "gene_disease"
    | "variant_gene"
    | "variant_disease"
    | "protein_interaction"
    | "gene_protein"
    | "publication_gene"
    | "publication_protein"
    | "publication_disease"
    | "gene_pathway"
    | "gene_biological_process"
    | "protein_molecular_function"
    | "biological_process_parent"
    | "molecular_function_parent";
  relationship_id: number;
  predicate:
    | "associated_with"
    | "located_in"
    | "interacts_with"
    | "encodes"
    | "mentions"
    | "discusses"
    | "studies"
    | "participates_in"
    | "involved_in"
    | "has_function"
    | "is_a";
  source_release?: string | null;
  evidence_code?: string | null;
  evidence_kind?: "structured_metadata" | "curated" | null;
  subject: RelationshipNode;
  object: RelationshipNode;
  source: string;
  source_identifier: string | null;
  source_url: string | null;
  imported_at: string | null;
  evidence_text: string | null;
  provenance_basis: "relationship_assertion" | "protein_record";
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export type SearchEntityType = "gene" | "protein" | "organism" | "publication";

export interface SearchMatchedField {
  field: string;
  value: string;
}

export interface SearchResult {
  entity_type: SearchEntityType;
  entity_id: number;
  primary_label: string;
  secondary_label: string | null;
  description: string | null;
  organism: {
    scientific_name: string;
    taxonomy_id: string | null;
  } | null;
  source: string;
  href: string | null;
  score: number;
  matched_fields: SearchMatchedField[];
}

export interface SearchCounts {
  gene: number;
  protein: number;
  organism: number;
  publication: number;
  total: number;
}

export interface SearchResponse {
  query: string;
  items: SearchResult[];
  counts: SearchCounts;
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface SearchSuggestion {
  entity_type: SearchEntityType;
  value: string;
  secondary_label: string | null;
  href: string | null;
}

export interface SearchSuggestionsResponse {
  query: string;
  items: SearchSuggestion[];
}

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
  };
}
