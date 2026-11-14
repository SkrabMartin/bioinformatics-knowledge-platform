import { PageHeader } from "../components/PageHeader";

export function AboutPage() {
  return (
    <div className="page-container">
      <PageHeader
        eyebrow="About the platform"
        title="About"
        description="Purpose, current scope and data policy of this installation."
      />
      <div className="about-grid">
        <section>
          <h2>Purpose</h2>
          <p>
            Make public biological knowledge easier to navigate without hiding where each record
            originated.
          </p>
        </section>
        <section>
          <h2>Current scope</h2>
          <p>
            Genes and proteins can be imported from NCBI and UniProt and searched alongside
            organisms. PubMed citations can be imported and searched with explicit provider links to
            locally stored genes. Diseases, variants, and sourced relationships are browsable. The
            graph explorer supports bounded traversal, node expansion and source inspection.
            Pathways, biological processes, molecular functions and direct ontology hierarchies can
            be browsed with source releases. Functional records are administrator-supplied;
            enrichment statistics and automatic ontology imports are not implemented. Administrators
            can queue bounded import batches, track each record and retry temporary provider
            failures. Imports preserve the original source metadata. Gene records retain
            source-reported aliases and reference sequence placements. Alias search leads to
            canonical gene records without merging genes that share a name. Ensembl transcript
            annotations can be imported for existing mapped genes and browsed with source release,
            assembly and coordinate context. Namespaced identifier mappings retain explicit source
            assertions and reported versions, so cross-database identity can be inspected.
          </p>
        </section>
        <section>
          <h2>Data policy</h2>
          <p>
            Starter records are clearly labeled development fixtures. Real provider imports are
            opt-in; search only returns records actually stored in the local database.
          </p>
        </section>
      </div>
    </div>
  );
}
