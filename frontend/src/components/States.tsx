interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function LoadingState({ label = "Loading records" }: { label?: string }) {
  return (
    <div className="state-panel" aria-live="polite" aria-busy="true">
      <span className="spinner" aria-hidden="true" />
      <div>
        <strong>{label}</strong>
        <p>Requesting structured data from the platform API.</p>
      </div>
    </div>
  );
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="state-panel state-panel--error" role="alert">
      <span className="state-symbol" aria-hidden="true">
        !
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

export function EmptyState({ entity }: { entity: string }) {
  return (
    <div className="state-panel">
      <span className="state-symbol" aria-hidden="true">
        ∅
      </span>
      <div>
        <strong>No {entity} are available</strong>
        <p>No records have been stored in this collection yet.</p>
      </div>
    </div>
  );
}
