import { DetailSection } from "./EntityDetail";
import type { GeneAlias, GeneGenomicLocation } from "../types/entities";

export function GeneContextPanel({
  aliases,
  locations,
}: {
  aliases: GeneAlias[];
  locations: GeneGenomicLocation[];
}) {
  return (
    <>
      <DetailSection title="Source-reported aliases">
        {aliases.length ? (
          <ul className="related-list">
            {aliases.map((alias) => (
              <li key={alias.id}>
                <strong>{alias.alias}</strong>
                <span>
                  {alias.source} · {alias.source_identifier}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="context-note">No source-backed aliases have been imported.</p>
        )}
        <p className="context-note">
          Aliases can be shared by different genes. Search results retain each gene&apos;s identity
          and organism.
        </p>
      </DetailSection>
      <DetailSection title="Reference sequence placements">
        {locations.length ? (
          <ul className="related-list">
            {locations.map((location) => (
              <li key={location.id}>
                <strong>{location.sequence_accession}</strong>
                <span>
                  {location.start_position.toLocaleString()}–
                  {location.end_position.toLocaleString()}
                  {" · Strand "}
                  {location.strand}
                </span>
                <span>
                  {location.source} · {location.source_identifier}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="context-note">No reference sequence placements have been imported.</p>
        )}
        <p className="context-note">
          These source observations use one-based inclusive coordinates. A sequence accession
          identifies a reference sequence, not a genome assembly. Earlier observations are retained;
          this list does not establish the current preferred assembly.
        </p>
      </DetailSection>
    </>
  );
}
