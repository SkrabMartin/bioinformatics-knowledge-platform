import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";

type Activity = {
  entity_type: string;
  jobs: Record<string, number>;
  items: Record<string, number>;
  last_activity_at: string | null;
};
type Report = {
  observed_at: string;
  worker_status: "unknown";
  scope: string;
  activity: Activity[];
};
const jobStates = ["queued", "running", "succeeded", "completed_with_errors", "cancelled", "total"];
const itemStates = [
  "pending",
  "running",
  "retry_wait",
  "succeeded",
  "failed",
  "cancelled",
  "total",
];
function columns(kind: "jobs" | "items", states: string[]): Column<Activity>[] {
  return [
    { key: "type", heading: "Record type", render: (row) => row.entity_type },
    ...states.map((state) => ({
      key: state,
      heading: state.replaceAll("_", " "),
      render: (row: Activity) => <span className="mono">{row[kind][state] ?? 0}</span>,
    })),
  ];
}
export function ImportStatusPage() {
  const { data, error, loading, retry } = useEntity<Report>("import-status");
  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Data engineering"
        title="Import activity"
        description="Read-only counts from the durable import queue."
        showSearch={false}
      />
      <p className="context-note">
        Queue states do not establish that a worker is currently online. Worker availability is
        unknown; a running item may have been interrupted. Direct CLI imports are not tracked here.
        No periodic synchronization is enabled by this page.
      </p>
      <button type="button" onClick={retry} disabled={loading}>
        Refresh activity
      </button>
      {loading && <LoadingState label="Loading import activity" />}
      {error && <ErrorState message={error} onRetry={retry} />}
      {!loading && !error && data && (
        <>
          <p className="context-note">
            Snapshot observed:{" "}
            <span className="mono">{new Date(data.observed_at).toLocaleString()}</span>. Historical
            totals include completed jobs, not just work waiting to run.
          </p>
          {!data.activity.some((row) => row.jobs.total > 0) && (
            <EmptyState title="No queued import history">
              Biological records may already exist from direct CLI imports.
            </EmptyState>
          )}
          <h2>Import jobs</h2>
          <DataTable
            caption="Import job counts by record type"
            columns={columns("jobs", jobStates)}
            items={data.activity}
            getKey={(row) => row.entity_type}
          />
          <h2>Import items</h2>
          <DataTable
            caption="Import item counts by record type"
            columns={columns("items", itemStates)}
            items={data.activity}
            getKey={(row) => row.entity_type}
          />
          <h2>Last stored queue activity</h2>
          <DataTable
            caption="Last queue activity by record type"
            columns={[
              { key: "type", heading: "Record type", render: (row) => row.entity_type },
              {
                key: "updated",
                heading: "Last recorded update",
                render: (row) => (
                  <span className="mono">
                    {row.last_activity_at
                      ? new Date(row.last_activity_at).toLocaleString()
                      : "No queue history"}
                  </span>
                ),
              },
            ]}
            items={data.activity}
            getKey={(row) => row.entity_type}
          />
          <p className="context-note">
            Dataset jobs fetch GEO Series metadata only. They do not download experimental files or
            resolve publication links automatically. Creating or cancelling jobs requires
            administrator access. Identifiers, results and error details are not published here.
          </p>
        </>
      )}
    </div>
  );
}
