import type { EntityRelationship, RelatedEntityType, RelationshipNode } from "../../types/entities";

export type RelationshipType = EntityRelationship["relationship_type"];
export interface GraphNode extends RelationshipNode {
  id: string;
  depth: number;
}
export interface GraphEdge {
  id: string;
  source_node: string;
  target_node: string;
  directed: boolean;
  assertion: EntityRelationship;
}
export type TruncationReason =
  "node_limit" | "edge_limit" | "scan_limit" | "time_budget" | "data_changed";
export interface GraphLimits {
  depth: number;
  max_nodes: number;
  max_edges: number;
  entity_types: RelatedEntityType[];
  relationship_types: RelationshipType[];
}
export interface GraphResponse {
  root_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  limits: GraphLimits;
  truncated: boolean;
  truncation_reasons: TruncationReason[];
  scanned_edges: number;
}
export type GraphSelection = { kind: "node" | "edge"; id: string };

export const entityTypes: RelatedEntityType[] = [
  "gene",
  "protein",
  "disease",
  "variant",
  "publication",
];
export const relationshipLabels: Record<RelationshipType, string> = {
  gene_protein: "Gene encodes protein",
  gene_disease: "Gene–disease association",
  variant_gene: "Variant in gene",
  variant_disease: "Variant–disease association",
  protein_interaction: "Protein interaction",
  publication_gene: "Publication mentions gene",
  publication_protein: "Publication discusses protein",
  publication_disease: "Publication studies disease",
};
export const truncationLabels: Record<TruncationReason, string> = {
  node_limit: "Node limit reached",
  edge_limit: "Relationship limit reached",
  scan_limit: "Candidate scan limit reached",
  time_budget: "Time budget reached",
  data_changed: "Some records changed while loading; refresh to retry",
};
