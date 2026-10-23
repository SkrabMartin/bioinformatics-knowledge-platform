import type { KnowledgeKind } from "../../types/entities";

export const knowledgeCollections: Record<
  KnowledgeKind,
  {
    title: string;
    singular: string;
    path: string;
    detail: string;
    resource: string;
    description: string;
  }
> = {
  pathway: {
    title: "Pathways",
    singular: "Pathway",
    path: "/pathways",
    detail: "/pathway",
    resource: "pathways",
    description: "Explore source-defined pathways and their directly recorded gene memberships.",
  },
  biological_process: {
    title: "Biological processes",
    singular: "Biological process",
    path: "/biological-processes",
    detail: "/biological-process",
    resource: "ontology/biological_process",
    description:
      "Browse GO biological processes, direct gene annotations and sourced is_a hierarchy.",
  },
  molecular_function: {
    title: "Molecular functions",
    singular: "Molecular function",
    path: "/molecular-functions",
    detail: "/molecular-function",
    resource: "ontology/molecular_function",
    description:
      "Browse GO molecular functions, direct protein annotations and sourced is_a hierarchy.",
  },
};
