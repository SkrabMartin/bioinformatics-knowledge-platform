import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="page-container not-found">
      <span className="eyebrow">404 · Not found</span>
      <h1>Page not found</h1>
      <p>No page exists at this address. Check the URL or search for the record.</p>
      <Link className="button" to="/search">
        Search records
      </Link>
    </div>
  );
}
