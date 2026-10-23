import { NavLink, Outlet } from "react-router-dom";

function BrandMark() {
  return (
    <svg aria-hidden="true" className="brand-mark" viewBox="0 0 42 42">
      <path d="M13 7c11 4 7 24 18 28M29 7c-11 4-7 24-18 28" />
      <path d="M12 13h18M11 21h20M12 29h18" />
    </svg>
  );
}

const navigation = [
  ["/", "Home"],
  ["/search", "Search"],
  ["/genes", "Genes"],
  ["/proteins", "Proteins"],
  ["/diseases", "Diseases"],
  ["/variants", "Variants"],
  ["/publications", "Publications"],
  ["/graph", "Graph"],
  ["/about", "About"],
];

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <NavLink className="brand" to="/" aria-label="BioKnowledge home">
            <BrandMark />
            <span>
              <strong>BioKnowledge</strong>
              <small>Research platform</small>
            </span>
          </NavLink>
          <nav aria-label="Primary navigation">
            {navigation.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === "/"}>
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <div className="fixture-notice" role="note">
        <span>Development environment</span>
        Demo fixtures are labeled individually; provider-backed records show their source.
      </div>
      <main>
        <Outlet />
      </main>
      <footer>
        <div>
          <strong>BioKnowledge Platform</strong>
          <p>Open infrastructure for traceable biological knowledge.</p>
        </div>
        <p>Phase 6 · Knowledge graph</p>
      </footer>
    </div>
  );
}
