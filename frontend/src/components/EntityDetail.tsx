import type { ReactNode } from "react";

import type { ProvenanceFields } from "../types/entities";
import { ProvenanceBadge } from "./ProvenanceBadge";

export function DetailHeader({
  type,
  title,
  subtitle,
  organism,
}: {
  type: string;
  title: string;
  subtitle: string;
  organism?: string;
}) {
  return (
    <header className="detail-hero">
      <span className="eyebrow">{type}</span>
      <h1>{title}</h1>
      <p className="detail-subtitle">{subtitle}</p>
      {organism && <p className="detail-organism">{organism}</p>}
    </header>
  );
}

export function DetailSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="detail-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function FactGrid({ facts }: { facts: { label: string; value: ReactNode }[] }) {
  return (
    <dl className="fact-grid">
      {facts.map((fact) => (
        <div key={fact.label}>
          <dt>{fact.label}</dt>
          <dd>{fact.value ?? "Not available"}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ProvenancePanel({ record }: { record: ProvenanceFields }) {
  return (
    <div className="source-panel">
      <div>
        <span className="source-label">Provider</span>
        <ProvenanceBadge source={record.source} />
      </div>
      <div>
        <span className="source-label">Source identifier</span>
        <code>{record.source_identifier ?? "Not available"}</code>
      </div>
      <div>
        <span className="source-label">Retrieved</span>
        <span>{formatDate(record.imported_at)}</span>
      </div>
      {record.source_url && (
        <a href={record.source_url} rel="noreferrer" target="_blank">
          Open provider record <span aria-hidden="true">↗</span>
        </a>
      )}
    </div>
  );
}

function formatDate(value: string | null) {
  if (!value) return "Not available";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString();
}
