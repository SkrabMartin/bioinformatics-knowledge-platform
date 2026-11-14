import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

const navigation = [
  ["/", "Home"],
  ["/search", "Search"],
  ["/genes", "Genes"],
  ["/transcripts", "Transcripts"],
  ["/proteins", "Proteins"],
  ["/diseases", "Diseases"],
  ["/phenotypes", "Phenotypes"],
  ["/variants", "Variants"],
  ["/publications", "Publications"],
  ["/datasets", "Datasets"],
  ["/pathways", "Pathways"],
  ["/graph", "Graph"],
  ["/analysis/gene-overlap", "Gene overlap"],
  ["/genomics/intervals", "Genomic intervals"],
  ["/data-quality", "Data quality"],
  ["/import-status", "Import activity"],
  ["/about", "About"],
];

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <NavLink
            className="brand"
            to="/"
            aria-label="BioKnowledge home"
            onClick={() => setMenuOpen(false)}
          >
            <span className="brand-code">BKP</span>
            <span>BioKnowledge Platform</span>
          </NavLink>
          <button
            className="nav-toggle"
            type="button"
            aria-expanded={menuOpen}
            aria-controls="site-nav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? "Close menu" : "Menu"}
          </button>
          <nav
            id="site-nav"
            className={`site-nav${menuOpen ? " is-open" : ""}`}
            aria-label="Primary navigation"
          >
            {navigation.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === "/"} onClick={() => setMenuOpen(false)}>
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <div className="fixture-notice" role="note">
        <span>
          <strong>Development environment.</strong> Demo fixtures are labeled individually;
          provider-backed records show their source.
        </span>
      </div>
      <main>
        <Outlet />
      </main>
      <footer>
        <div>
          <span>BioKnowledge Platform v0.24</span>
          <Link to="/about">Scope and data policy</Link>
        </div>
      </footer>
    </div>
  );
}
