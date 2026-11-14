import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ErrorState, LoadingState } from "../components/States";
import { useEntity } from "../hooks/useEntity";
import { getEntity } from "../services/api";
import type { Page, Transcript, TranscriptSummary } from "../types/entities";

type Match = TranscriptSummary & {
  gene_symbol: string;
  gene_href: string;
  transcript_href: string;
  overlap_start: number;
  overlap_end: number;
  overlap_bases: number;
};
type Report = {
  query: {
    assembly_name: string;
    sequence_region: string;
    taxonomy_id: string;
    coordinate_system: string;
  };
  normalized_start: number;
  normalized_end: number;
  method: string;
  interpretation: string;
  observed_at: string;
  matches: Page<Match>;
};
const columns: Column<Match>[] = [
  {
    key: "transcript",
    heading: "Transcript",
    render: (r) => (
      <Link className="mono" to={r.transcript_href}>
        {r.ensembl_transcript_id}
        {r.version === null ? "" : `.${r.version}`}
      </Link>
    ),
  },
  {
    key: "gene",
    heading: "Gene",
    render: (r) => (
      <Link className="mono" to={r.gene_href}>
        {r.gene_symbol}
      </Link>
    ),
  },
  {
    key: "span",
    heading: "Stored span (1-based closed)",
    render: (r) => (
      <span className="mono">
        {r.start_position}–{r.end_position} ({r.strand})
      </span>
    ),
  },
  {
    key: "overlap",
    heading: "Span overlap (reference bases)",
    render: (r) => (
      <span className="mono">
        {r.overlap_start}–{r.overlap_end} · {r.overlap_bases} bp
      </span>
    ),
  },
  {
    key: "source",
    heading: "Source / release",
    render: (r) => (
      <span>
        {r.source_url ? (
          <a href={r.source_url} target="_blank" rel="noreferrer">
            {r.source}
          </a>
        ) : (
          r.source
        )}{" "}
        · <span className="mono">{r.source_release}</span>
      </span>
    ),
  },
];
function Results({ resource, onPage }: { resource: string; onPage: (page: number) => void }) {
  const { data, loading, error, retry } = useEntity<Report>(resource);
  if (loading) return <LoadingState label="Finding overlapping transcript spans" />;
  if (error) return <ErrorState message={error} onRetry={retry} />;
  if (!data) return null;
  return (
    <section aria-label="Transcript interval results">
      <h2>Stored transcript spans</h2>
      <p className="mono">
        {data.query.assembly_name} · {data.query.sequence_region}:{data.normalized_start}–
        {data.normalized_end} · Taxonomy {data.query.taxonomy_id}
      </p>
      <p className="context-note">
        Input: {data.query.coordinate_system.replaceAll("_", " ")}. Displayed query, transcript and
        overlap positions are 1-based closed. Coordinates follow the reference axis even for
        reverse-strand transcripts.
      </p>
      <p>{data.matches.total} matching stored transcript spans.</p>
      {data.matches.items.length ? (
        <DataTable
          caption="Overlapping transcript spans"
          columns={columns}
          items={data.matches.items}
          getKey={(r) => r.id}
        />
      ) : data.matches.total > 0 ? (
        <p>
          No records on this page.{" "}
          <button type="button" onClick={() => onPage(1)}>
            Return to first page
          </button>
        </p>
      ) : (
        <p>
          No stored transcript spans match this interval. This does not establish biological
          absence.
        </p>
      )}
      <Pagination
        page={data.matches.page}
        pages={data.matches.pages}
        total={data.matches.total}
        onPageChange={onPage}
      />
      <p className="context-note">{data.interpretation}</p>
      <p className="context-note">
        Method: <span className="mono">{data.method}</span>. Observed{" "}
        {new Date(data.observed_at).toLocaleString()}. Source retrieval dates remain available on
        transcript details.
      </p>
    </section>
  );
}
export function GenomicIntervalsPage() {
  const [taxonomy, setTaxonomy] = useState("9606"),
    [assembly, setAssembly] = useState(""),
    [region, setRegion] = useState(""),
    [start, setStart] = useState(""),
    [end, setEnd] = useState("");
  const [coordinates, setCoordinates] = useState("one_based_closed"),
    [strand, setStrand] = useState("");
  const [base, setBase] = useState<string | null>(null),
    [page, setPage] = useState(1),
    [run, setRun] = useState(0);
  const [message, setMessage] = useState<string | null>(null),
    [exampleLoading, setExampleLoading] = useState(false);
  async function example() {
    setMessage(null);
    setExampleLoading(true);
    try {
      const records = await getEntity<Page<Transcript>>("transcripts?page=1&page_size=1");
      const record = records.items[0];
      const tax = record?.gene.organism.taxonomy_id;
      if (!record || !tax || !/^[1-9][0-9]{0,15}$/.test(tax) || record.start_position > 1e12) {
        setMessage("No usable stored transcript example is available. Enter an explicit interval.");
        return;
      }
      setTaxonomy(tax);
      setAssembly(record.assembly_name);
      setRegion(record.sequence_region);
      setStart(String(record.start_position));
      setEnd(String(Math.min(record.end_position, record.start_position + 999)));
      setCoordinates("one_based_closed");
      setStrand("");
      setBase(null);
      setMessage(
        `Example from stored transcript ${record.ensembl_transcript_id}, up to its first 1,000 reference bases. Submit to browse.`,
      );
    } catch {
      setMessage("Stored example could not be loaded. Enter an interval manually or retry.");
    } finally {
      setExampleLoading(false);
    }
  }
  function browse(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    const first = Number(start),
      last = Number(end),
      closed = first + (coordinates === "zero_based_half_open" ? 1 : 0);
    if (
      !Number.isSafeInteger(first) ||
      !Number.isSafeInteger(last) ||
      closed < 1 ||
      last < closed ||
      last - closed + 1 > 10000000 ||
      last > 1e12
    ) {
      setMessage("Enter a nonempty valid interval of at most 10,000,000 bases.");
      setBase(null);
      return;
    }
    const params = new URLSearchParams({
      taxonomy_id: taxonomy,
      assembly_name: assembly.trim(),
      sequence_region: region.trim(),
      start: String(first),
      end: String(last),
      coordinate_system: coordinates,
      page_size: "20",
    });
    if (strand) params.set("strand", strand);
    setBase(`genomics/transcript-overlaps?${params}`);
    setPage(1);
    setRun((v) => v + 1);
  }
  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Genomics toolkit"
        title="Genomic intervals"
        description="Find locally stored whole transcript spans overlapping an exact reference interval."
        showSearch={false}
      />
      <p className="context-note">
        Select the exact stored assembly, sequence region and organism. Region names such as 17 and
        chr17 are not treated as aliases. No reference sequence, exon structure, liftover or variant
        effect is calculated. Inputs travel in GET request URLs.
      </p>
      <p className="context-note">
        Equivalent intervals: 1-based 100–200 = 0-based 99–200. Switching the input mode
        reinterprets entered numbers; it does not convert them automatically.
      </p>
      <form onSubmit={browse}>
        <div className="form-row">
          <label>
            NCBI taxonomy ID
            <input
              required
              pattern="[1-9][0-9]{0,15}"
              maxLength={16}
              value={taxonomy}
              onChange={(e) => setTaxonomy(e.target.value)}
            />
          </label>
          <label>
            Assembly name
            <input
              required
              maxLength={128}
              value={assembly}
              onChange={(e) => setAssembly(e.target.value)}
            />
          </label>
          <label>
            Sequence region
            <input
              required
              maxLength={128}
              value={region}
              onChange={(e) => setRegion(e.target.value)}
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Input coordinates
            <select value={coordinates} onChange={(e) => setCoordinates(e.target.value)}>
              <option value="one_based_closed">1-based closed</option>
              <option value="zero_based_half_open">0-based half-open</option>
            </select>
          </label>
          <label>
            Start
            <input
              required
              type="number"
              min={coordinates === "one_based_closed" ? 1 : 0}
              max={1e12}
              step={1}
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label>
            End
            <input
              required
              type="number"
              min={1}
              max={1e12}
              step={1}
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
          <label>
            Transcript strand
            <select value={strand} onChange={(e) => setStrand(e.target.value)}>
              <option value="">Both strands</option>
              <option value="+">Forward (+)</option>
              <option value="-">Reverse (−)</option>
            </select>
          </label>
        </div>
        <div className="form-row">
          <button type="submit">Browse transcript spans</button>
          <button type="button" disabled={exampleLoading} onClick={() => void example()}>
            {exampleLoading ? "Loading stored example…" : "Use stored transcript example"}
          </button>
        </div>
      </form>
      {message && <p role="status">{message}</p>}
      {base && (
        <>
          <p className="context-note">
            Results reflect the last submitted interval. Resubmit after editing the form.
          </p>
          <Results
            key={`${base}:${page}:${run}`}
            resource={`${base}&page=${page}`}
            onPage={setPage}
          />
        </>
      )}
    </div>
  );
}
