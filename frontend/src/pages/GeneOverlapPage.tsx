import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";

type Gene = {
  id: number;
  symbol: string;
  name: string;
  href: string;
  source: string;
  source_identifier: string | null;
  source_url: string | null;
  imported_at: string | null;
  updated_at: string;
};
type Input = {
  input_count: number;
  unique_inputs: string[];
  duplicates_removed: number;
  unresolved: string[];
  matched_inputs: Record<string, number>;
  resolved_gene_count: number;
};
type Report = {
  method: string;
  software_version: string;
  computed_at: string;
  namespace: string;
  taxonomy_id: string;
  coverage_complete: boolean;
  left: Input;
  right: Input;
  metrics: {
    left_size: number;
    right_size: number;
    intersection_size: number;
    union_size: number;
    jaccard: number | null;
  };
  shared: Gene[];
  left_only: Gene[];
  right_only: Gene[];
  interpretation: string;
};
const columns: Column<Gene>[] = [
  {
    key: "symbol",
    heading: "Gene",
    render: (g) => (
      <Link className="mono" to={g.href}>
        {g.symbol}
      </Link>
    ),
  },
  { key: "name", heading: "Name", render: (g) => g.name },
  {
    key: "source",
    heading: "Source",
    render: (g) =>
      g.source_url ? (
        <a href={g.source_url} target="_blank" rel="noreferrer">
          {g.source}
        </a>
      ) : (
        g.source
      ),
  },
];
function Results({ resource }: { resource: string }) {
  const { data, loading, error, retry } = useEntity<Report>(resource);
  const [downloadError, setDownloadError] = useState(false);
  if (loading) return <LoadingState label="Comparing local gene sets" />;
  if (error) return <ErrorState message={error} onRetry={retry} />;
  if (!data) return null;
  function download() {
    if (!data) return;
    try {
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2) + "\n"], {
          type: "application/json;charset=utf-8",
        }),
      );
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "bkp-gene-overlap.json";
      try {
        document.body.appendChild(anchor);
        anchor.click();
      } finally {
        anchor.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
      setDownloadError(false);
    } catch {
      setDownloadError(true);
    }
  }
  return (
    <section aria-label="Gene overlap result">
      <h2>Resolved gene set comparison</h2>
      <p className="context-note">{data.interpretation}</p>
      {!data.coverage_complete && (
        <p role="status">
          Partial resolution: unresolved identifiers are excluded from all set sizes and the index.
        </p>
      )}
      <dl>
        <dt>Left resolved genes</dt>
        <dd className="mono">{data.metrics.left_size}</dd>
        <dt>Right resolved genes</dt>
        <dd className="mono">{data.metrics.right_size}</dd>
        <dt>Intersection</dt>
        <dd className="mono">{data.metrics.intersection_size}</dd>
        <dt>Union</dt>
        <dd className="mono">{data.metrics.union_size}</dd>
        <dt>Jaccard index (intersection / union)</dt>
        <dd className="mono">
          {data.metrics.jaccard === null
            ? "Undefined (empty resolved union)"
            : data.metrics.jaccard.toFixed(4)}
        </dd>
      </dl>
      {(["left", "right"] as const).map((side) => (
        <section key={side}>
          <h3>{side === "left" ? "Left" : "Right"} input coverage</h3>
          <p>
            {data[side].input_count} inputs · {data[side].duplicates_removed} duplicate inputs
            removed · {data[side].resolved_gene_count} resolved genes.
          </p>
          <p>
            Unresolved: <span className="mono">{data[side].unresolved.join(", ") || "None"}</span>
          </p>
        </section>
      ))}
      {(
        [
          ["Shared genes", data.shared],
          ["Left only", data.left_only],
          ["Right only", data.right_only],
        ] as [string, Gene[]][]
      ).map(([title, items]) => (
        <section key={title}>
          <h3>{title}</h3>
          {items.length ? (
            <DataTable caption={title} columns={columns} items={items} getKey={(g) => g.id} />
          ) : (
            <p>No genes in this resolved set.</p>
          )}
        </section>
      ))}
      <p className="context-note">
        Method: <span className="mono">{data.method}</span> · BKP {data.software_version} · Taxonomy{" "}
        {data.taxonomy_id} · {data.namespace}. Computed{" "}
        {new Date(data.computed_at).toLocaleString()}.
      </p>
      <button type="button" onClick={download}>
        Download analysis JSON
      </button>
      {downloadError && (
        <p role="alert">Download failed. The analysis remains available; try again.</p>
      )}
    </section>
  );
}
export function GeneOverlapPage() {
  const [left, setLeft] = useState(""),
    [right, setRight] = useState(""),
    [namespace, setNamespace] = useState("symbol"),
    [taxonomy, setTaxonomy] = useState("9606");
  const [run, setRun] = useState(0);
  const [resource, setResource] = useState<string | null>(null),
    [validation, setValidation] = useState<string | null>(null);
  function compare(event: FormEvent) {
    event.preventDefault();
    setValidation(null);
    const lists = [left, right].map((value) =>
      value
        .trim()
        .split(/[\s,;]+/)
        .filter(Boolean),
    );
    if (
      lists.some(
        (values) =>
          values.length < 1 || values.length > 50 || values.some((value) => value.length > 64),
      )
    ) {
      setValidation("Enter 1–50 exact identifiers per list, at most 64 characters each.");
      setResource(null);
      return;
    }
    const params = new URLSearchParams({ namespace, taxonomy_id: taxonomy });
    lists[0].forEach((value) => params.append("left", value));
    lists[1].forEach((value) => params.append("right", value));
    setResource(`analysis/gene-overlap?${params}`);
    setRun((value) => value + 1);
  }
  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Bioinformatics analysis"
        title="Gene list overlap"
        description="Compare two sets of exactly resolved local genes."
        showSearch={false}
      />
      <p className="context-note">
        Exact, case-sensitive symbols or unversioned registered NCBI/Ensembl identifiers, within one
        explicit organism. No alias/fuzzy matching or external lookup. The small local catalogue
        limits coverage. This is not pathway enrichment or a significance test.
      </p>
      <p className="context-note">
        Inputs travel in GET request URLs and can appear in proxy logs. No files are uploaded or
        analysis history saved by BKP.
      </p>
      <form onSubmit={compare}>
        <div className="form-row">
          <label>
            Identifier type
            <select value={namespace} onChange={(e) => setNamespace(e.target.value)}>
              <option value="symbol">Gene symbol</option>
              <option value="ncbi_gene">NCBI Gene ID</option>
              <option value="ensembl_gene">Unversioned Ensembl Gene ID</option>
            </select>
          </label>
          <label>
            NCBI taxonomy ID
            <input
              value={taxonomy}
              onChange={(e) => setTaxonomy(e.target.value)}
              pattern="[1-9][0-9]{0,15}"
              maxLength={16}
              required
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Left gene list
            <textarea
              className="mono"
              rows={6}
              value={left}
              onChange={(e) => setLeft(e.target.value)}
              maxLength={3300}
              required
            />
          </label>
          <label>
            Right gene list
            <textarea
              className="mono"
              rows={6}
              value={right}
              onChange={(e) => setRight(e.target.value)}
              maxLength={3300}
              required
            />
          </label>
        </div>
        <p className="context-note">
          Separate identifiers with whitespace, commas or semicolons. Maximum 50 per list.
          Downloaded reports include input mappings, method version and current gene record source
          timestamps.
        </p>
        <div className="form-row">
          <button type="submit">Compare gene lists</button>
          <button
            type="button"
            onClick={() => {
              setLeft("TP53\nBRCA1");
              setRight("BRCA1\nPINK1");
              setNamespace("symbol");
              setTaxonomy("9606");
              setResource(null);
              setValidation(null);
            }}
          >
            Use local human example
          </button>
        </div>
      </form>
      {validation && <p role="alert">{validation}</p>}
      {resource && (
        <>
          <p className="context-note">
            Results below reflect the last submitted inputs. Submit again after editing the form.
          </p>
          <Results key={`${resource}:${run}`} resource={resource} />
        </>
      )}
    </div>
  );
}
