import type { ReactNode } from "react";

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function LoadingState({ label = "Loading records" }: { label?: string }) {
  return (
    <div className="state-panel" aria-live="polite" aria-busy="true">
      <span className="loader" aria-hidden="true" />
      <div>
        <strong>{label}</strong>
        <p>Requesting data from the platform API.</p>
      </div>
    </div>
  );
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="state-panel state-panel--error" role="alert">
      <span className="state-label" aria-hidden="true">
        Error
      </span>
      <div>
        <strong>Unable to load this collection</strong>
        <p>{message}</p>
        <button className="button button--small" onClick={onRetry} type="button">
          Try again
        </button>
      </div>
    </div>
  );
}

/** Empty result. Pass `entity` for a whole collection, or `title`/children for a filtered view. */
export function EmptyState({
  entity,
  title,
  children,
}: {
  entity?: string;
  title?: string;
  children?: ReactNode;
}) {
  const heading = title ?? (entity ? `No ${entity} are available` : null);
  const body = children ?? (entity ? "No records have been stored in this collection yet." : null);
  return (
    <div className="state-panel state-panel--empty">
      <span className="state-label" aria-hidden="true">
        Empty
      </span>
      <div>
        {heading && <strong>{heading}</strong>}
        {body && <p>{body}</p>}
      </div>
    </div>
  );
}
