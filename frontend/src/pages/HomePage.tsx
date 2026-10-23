import { EntityCard } from "../components/EntityCard";
import { SearchBox } from "../components/SearchBox";
import { ResearchEntryPanel } from "../components/ResearchEntryPanel";
import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <>
      <section className="hero">
        <div className="hero-content">
          <span className="eyebrow eyebrow--light">Connected biological knowledge</span>
          <h1>Move from an identifier to its biological context.</h1>
          <p>
            A traceable, open foundation for exploring genes, proteins, diseases, variants,
            publications, and sourced relationships among them.
          </p>
          <SearchBox />
          <p className="search-hint">
            Search genes, proteins, organisms, and publications already in the local database.
          </p>
          <Link className="hero-graph-link" to="/graph">
            Explore the relationship graph ↗
          </Link>
        </div>
        <ResearchEntryPanel />
      </section>

      <section className="content-section entity-overview" aria-labelledby="explore-heading">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Foundation collections</span>
            <h2 id="explore-heading">Explore the current knowledge model</h2>
          </div>
          <p>
            Explore biological records alongside imported scientific citations. Every visible record
            carries source metadata; starter fixtures are labeled as development data.
          </p>
        </div>
        <div className="card-grid">
          <EntityCard
            eyebrow="Entity type 01"
            title="Genes"
            description="Browse symbols, names, external identifiers, genomic fields, and organism context."
            href="/genes"
            icon="G"
          />
          <EntityCard
            eyebrow="Entity type 02"
            title="Proteins"
            description="Review accessions, encoded-by links, sequence metadata, and provenance."
            href="/proteins"
            icon="P"
          />
          <EntityCard
            eyebrow="Entity type 03"
            title="Diseases"
            description="Review sourced disease concepts and their recorded gene and variant associations."
            href="/diseases"
            icon="D"
          />
          <EntityCard
            eyebrow="Entity type 04"
            title="Variants"
            description="Inspect variant identifiers and follow evidence-linked genes and diseases."
            href="/variants"
            icon="V"
          />
          <EntityCard
            eyebrow="Scientific literature"
            title="Publications"
            description="Read imported citations, open source articles, and follow explicitly recorded entity links."
            href="/publications"
            icon="L"
          />
          <EntityCard
            eyebrow="Functional context"
            title="Pathways & ontology"
            description="Explore source-defined pathways, biological processes, molecular functions, and their directly recorded annotations."
            href="/pathways"
            icon="F"
          />
          <article className="entity-card entity-card--static">
            <span className="entity-icon" aria-hidden="true">
              O
            </span>
            <span className="eyebrow">Shared context</span>
            <h3>Organisms</h3>
            <p>Taxonomic context anchors genes and proteins while keeping names unambiguous.</p>
            <span className="card-link card-link--muted">Searchable by name or taxonomy ID</span>
          </article>
        </div>
      </section>

      <section className="content-section principles" aria-labelledby="principles-heading">
        <div>
          <span className="eyebrow">Built for scientific trust</span>
          <h2 id="principles-heading">Evidence before ornament.</h2>
        </div>
        <ol>
          <li>
            <strong>Traceable</strong>
            <span>Source and source identifier travel with each record.</span>
          </li>
          <li>
            <strong>Typed</strong>
            <span>Validated entities replace unstructured provider payloads.</span>
          </li>
          <li>
            <strong>Expandable</strong>
            <span>Typed literature links connect records to source publications.</span>
          </li>
        </ol>
      </section>
    </>
  );
}
