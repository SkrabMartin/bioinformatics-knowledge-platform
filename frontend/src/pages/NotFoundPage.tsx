import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="page-container not-found">
      <span className="eyebrow">404 · Not found</span>
      <h1>This route is outside the current knowledge map.</h1>
      <p>The page may not exist yet, or its address may have changed.</p>
      <Link className="button" to="/">
        Return home
      </Link>
    </div>
  );
}
