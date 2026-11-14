import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";

type QualityReport = {
  started_at: string;
  completed_at: string;
  refresh_after_days: number;
  fixture_policy: string;
  scope: string;
  checks: {
    code: string;
    title: string;
    severity: "info" | "warning" | "error";
    explanation: string;
    assessed: number;
    affected: number;
    examples: { id: number; label: string; href: string | null }[];
  }[];
};

export function DataQualityPage() {
  const [params, setParams] = useSearchParams();
  const value = Number(params.get("refresh_after_days") ?? "90");
  const days = Number.isInteger(value) && value >= 1 && value <= 3650 ? value : 90;
  const { data, loading, error, retry } = useEntity<QualityReport>(
    `data-quality?refresh_after_days=${days}`,
  );
  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Provenance and data quality"
        title="Data quality"
        description="Review stored source metadata, identifier consistency and refresh coverage."
        showSearch={false}
      />
      <p className="context-note">
        These checks describe stored metadata, not scientific validity. Coverage gaps and refresh
        reminders do not prove that biological information is incorrect. No automatic fixes or
        external lookups run here.
      </p>
      <form
        className="form-row"
        onSubmit={(event) => {
          event.preventDefault();
          setParams({ refresh_after_days: String(new FormData(event.currentTarget).get("days")) });
        }}
      >
        <label>
          Review retrievals older than (days)
          <input
            key={days}
            name="days"
            type="number"
            min="1"
            max="3650"
            required
            defaultValue={days}
          />
        </label>
        <button type="submit">Review data</button>
      </form>
      {loading && <LoadingState label="Reviewing data quality" />}
      {error && <ErrorState message={error} onRetry={retry} />}
      {!loading && !error && data && (
        <>
          <p className="context-note">
            {data.scope} {data.fixture_policy}
          </p>
          <p className="context-note">
            Review interval: {new Date(data.started_at).toLocaleString()} –{" "}
            {new Date(data.completed_at).toLocaleString()}. Concurrent imports may change counts
            during the review.
          </p>
          {!data.checks.some((check) => check.assessed > 0) && (
            <EmptyState title="No records assessed">
              An empty catalogue does not establish data quality.
            </EmptyState>
          )}
          <ul className="related-list">
            {data.checks.map((check) => (
              <li key={check.code}>
                <h2>{check.title}</h2>
                <p className="mono">
                  {check.affected} affected / {check.assessed} assessed ·{" "}
                  {check.severity === "info"
                    ? "Coverage / review"
                    : check.severity === "error"
                      ? "Conflict review"
                      : "Metadata review"}
                </p>
                <p>{check.explanation}</p>
                {check.examples.length > 0 && (
                  <>
                    <p>Examples (up to 5; counts can overlap across checks):</p>
                    <ul>
                      {check.examples.map((example) => (
                        <li key={example.id}>
                          {example.href ? (
                            <Link to={example.href}>{example.label}</Link>
                          ) : (
                            <span>{example.label} (organism taxonomy unavailable)</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {check.assessed > 0 && check.affected === 0 && <p>No findings for this check.</p>}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
