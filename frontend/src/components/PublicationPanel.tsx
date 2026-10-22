import { Link } from "react-router-dom";

import { useEntity } from "../hooks/useEntity";
import type { Page, Publication } from "../types/entities";
import { DetailSection } from "./EntityDetail";
import { PublicationCard } from "./PublicationCard";
import { ErrorState, LoadingState } from "./States";

export function PublicationPanel({ geneId }: { geneId: number }) {
  const { data, loading, error, retry } = useEntity<Page<Publication>>(
    `publications?gene_id=${geneId}&page=1&page_size=5&sort=newest`,
  );
  return (
    <DetailSection title="Associated publications">
      <div aria-live="polite">
        {loading && <LoadingState label="Loading associated publications" />}
        {!loading && error && <ErrorState message={error} onRetry={retry} />}
        {!loading && !error && data?.items?.length === 0 && (
          <p className="context-note">No sourced publications are linked to this gene locally.</p>
        )}
        {!loading &&
          !error &&
          data?.items?.map((publication) => (
            <PublicationCard key={publication.id} publication={publication} />
          ))}
        {!loading && !error && data && data.total > 5 && (
          <Link to={`/publications?gene_id=${geneId}`}>
            View all {data.total} associated publications
          </Link>
        )}
      </div>
    </DetailSection>
  );
}
