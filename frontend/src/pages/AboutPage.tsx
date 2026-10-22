import { PageHeader } from "../components/PageHeader";

export function AboutPage() {
  return (
    <div className="page-container">
      <PageHeader
        eyebrow="About the platform"
        title="A dependable substrate for biological discovery"
        description="The platform is being built in verified increments, beginning with typed entities and transparent provenance."
      />
      <div className="about-grid">
        <section>
          <span className="section-number">01</span>
          <h2>Mission</h2>
          <p>
            Make public biological knowledge easier to navigate without hiding where each record
            originated.
          </p>
        </section>
        <section>
          <span className="section-number">02</span>
          <h2>Current scope</h2>
          <p>
            Genes and proteins can be imported from NCBI and UniProt and searched alongside
            organisms. PubMed citations can be imported and searched with explicit provider links to
            locally stored genes. Diseases, variants, and sourced relationships are browsable.
          </p>
        </section>
        <section>
          <span className="section-number">03</span>
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
