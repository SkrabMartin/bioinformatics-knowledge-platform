export function ProvenanceBadge({ source }: { source: string }) {
  const isFixture = source === "development_fixture";
  return (
    <span className={`provenance${isFixture ? " provenance--fixture" : ""}`}>
      <span aria-hidden="true" />
      {isFixture ? "Demo fixture" : source}
    </span>
  );
}
