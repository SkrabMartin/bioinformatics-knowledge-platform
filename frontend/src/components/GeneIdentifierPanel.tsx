import { DetailSection } from "./EntityDetail";
import type { GeneExternalIdentifier } from "../types/entities";

export function GeneIdentifierPanel({ identifiers }: { identifiers: GeneExternalIdentifier[] }) {
  return (
    <DetailSection title="Source-backed identifier mappings">
      {identifiers.length ? (
        <ul className="related-list">
          {identifiers.map((identity) => (
            <li key={identity.id}>
              <strong>
                {identity.namespace === "ncbi_gene" ? "NCBI Gene" : "Ensembl Gene"} ·{" "}
                {identity.accession}
              </strong>
              <ul>
                {identity.evidence.map((evidence) => (
                  <li key={evidence.id}>
                    <span>Reported identifier: {evidence.reported_accession}</span>
                    <span>
                      {evidence.source} · source record {evidence.source_identifier}
                    </span>
                    {evidence.source_record_version && (
                      <span>Provider record version: {evidence.source_record_version}</span>
                    )}
                    {evidence.source_url && (
                      <a href={evidence.source_url} target="_blank" rel="noreferrer">
                        View mapping source
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      ) : (
        <p className="context-note">
          No source-backed identifier assertions have been recorded. Legacy identifier fields alone
          do not establish mapping provenance.
        </p>
      )}
      <p className="context-note">
        Namespaces distinguish identifiers from names and aliases. Source-reported versions are
        retained separately from stable identity; this is not a historical gene snapshot.
      </p>
    </DetailSection>
  );
}
