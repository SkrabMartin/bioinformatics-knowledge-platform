import { Link } from "react-router-dom";

import { DataTable, type Column } from "../components/DataTable";
import { ResearchEntryPanel } from "../components/ResearchEntryPanel";
import { SearchBox } from "../components/SearchBox";

interface Collection {
  title: string;
  href: string | null;
  contents: string;
}

const collections: Collection[] = [
  {
    title: "Genes",
    href: "/genes",
    contents: "Symbols, names, aliases, external identifiers, reference sequence placements.",
  },
  {
    title: "Transcripts",
    href: "/transcripts",
    contents: "Ensembl transcript annotations with parent gene, assembly and source release.",
  },
  {
    title: "Proteins",
    href: "/proteins",
    contents: "Accessions, encoding gene, sequence length and function statement.",
  },
  {
    title: "Diseases",
    href: "/diseases",
    contents: "Disease concepts with MONDO and Disease Ontology identifiers.",
  },
  {
    title: "Phenotypes",
    href: "/phenotypes",
    contents: "HPO-identified terms and their sourced disease annotations.",
  },
  {
    title: "Variants",
    href: "/variants",
    contents: "rsID and HGVS identifiers, sourced genomic placements, linked genes and diseases.",
  },
  {
    title: "Publications",
    href: "/publications",
    contents: "Imported citations, source keywords and recorded entity links.",
  },
  {
    title: "Datasets",
    href: "/datasets",
    contents: "GEO Series discovery metadata with links to the repository record.",
  },
  {
    title: "Pathways and GO terms",
    href: "/pathways",
    contents:
      "Source-defined pathways, biological processes, molecular functions and cellular components.",
  },
  {
    title: "Organisms",
    href: null,
    contents: "Taxonomic context of genes and proteins. Searchable by name or taxonomy ID.",
  },
  {
    title: "Graph",
    href: "/graph",
    contents: "Bounded traversal of stored relationships with source inspection and export.",
  },
  {
    title: "Data quality",
    href: "/data-quality",
    contents: "Review of stored source metadata, identifier consistency and refresh coverage.",
  },
];

const columns: Column<Collection>[] = [
  {
    key: "collection",
    heading: "Collection",
    render: (item) =>
      item.href ? (
        <Link className="entity-link" to={item.href}>
          {item.title}
        </Link>
      ) : (
        <strong>{item.title}</strong>
      ),
  },
  { key: "contents", heading: "Contents", render: (item) => item.contents },
];

export function HomePage() {
  return (
    <div className="page-container home">
      <div className="home-grid">
        <section aria-labelledby="home-title">
          <h1 id="home-title">Search stored records</h1>
          <SearchBox />
          <p className="search-hint">
            Searches genes, proteins, transcripts, diseases, phenotypes, variants, pathways, GO
            terms, organisms, publications and datasets in the local database. Enter a symbol, name,
            accession or identifier such as an rsID, HGVS expression, PMID, DOI, GO, HPO or MONDO
            ID.
          </p>
        </section>
        <ResearchEntryPanel />
      </div>
      <section aria-labelledby="collections-heading">
        <h2 id="collections-heading">Collections</h2>
        <DataTable
          caption="Collections"
          columns={columns}
          items={collections}
          getKey={(item) => item.title}
        />
        <p className="context-note">
          Every record carries its source and source identifier. Starter fixtures are labeled as
          development data.
        </p>
      </section>
    </div>
  );
}
