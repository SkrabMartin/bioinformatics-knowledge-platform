# Phenotypes and qualified disease assertions — 0.14.0

This is an initial part of long-term roadmap Phase 7. It adds stored HPO-identified
phenotype terms and explicitly sourced disease–phenotype assertions. It does not
complete Phase 7 or automatically populate either catalogue.

## Scientific and identity contract

A term has an internal numeric ID, unique `HP:` plus seven-digit identifier, name,
optional description, source record identifier, source release, HTTP(S) source URL
and explicit retrieval timestamp. Create requests require a timezone-aware timestamp.
The API validates identifier shape, not membership or label correctness in a live
HPO release. Authenticated administrators remain responsible for source accuracy.

Each disease assertion requires an existing disease and phenotype, an explicit
`qualifier` of `present` or `excluded`, an evidence kind (`curated` or
`structured_metadata`), a nonblank reference, source record identifier, release,
source URL and retrieval timestamp. Optional evidence code preserves provider text;
no code, frequency, onset, certainty or biological mechanism is inferred.

The distinction is motivated by the HPO annotation format, which preserves negative
`NOT` annotations separately from ordinary disease features. See the
[official phenotype.hpoa documentation](https://github.com/obophenotype/human-phenotype-ontology/blob/master/docs/annotations/phenotype_hpoa.md).
BKP uses its own explicit `excluded` value; it does not claim to implement the full
HPO annotation format or all of its modifiers.

An excluded assertion must never be presented as a positive association. The API and
UI preserve both polarities, including conflicting source assertions. Duplicate
assertions are constrained by disease, phenotype, source, source record, release and
qualifier. Distinct releases and qualifiers can coexist. Missing annotations do not
establish either presence or exclusion. These are disease-level source assertions,
not patient observations or diagnostic results.

## HTTP interface

Public read routes:

- `GET /api/v1/phenotypes?page=1&page_size=20&q=...` filters HPO ID/name with
  escaped literal wildcards and bounded pagination.
- `GET /api/v1/phenotypes/{id}` returns the term and its provenance.
- `GET /api/v1/diseases/{id}/phenotypes` and
  `GET /api/v1/phenotypes/{id}/diseases` return paginated, sourced assertions in
  either direction. Missing parent entities return 404.

Administrator routes (protected by the existing fail-closed bearer-token dependency):

- `POST /api/v1/phenotypes` creates a sourced term; duplicate HPO identity returns 409.
- `POST /api/v1/diseases/{id}/phenotypes` creates a qualified assertion; duplicate
  source assertions return 409 and missing targets return 404.

Writes remain disabled when the private admin token is unset. The public reverse
proxy continues to block write methods. No public write UI, edit/delete endpoint,
automatic backfill, background import or scheduled HPO synchronization is added.
Provenance metadata and references are retained as supplied, not independently
verified by contacting providers.

## Navigation and search

`/phenotypes` provides a filtered catalogue; `/phenotype/{id}` shows the term,
release, provenance and disease assertions. Disease detail now includes phenotype
annotations. Both views display qualifier, evidence kind/code, reference, release,
retrieval time and provider link. They paginate assertions rather than silently
collapsing conflicting sources into one inferred fact.

Unified search and suggestions add the `phenotype` category, HPO ID/name/description
matching, a new count and detail links. Search now supports eleven categories.
Clients with closed entity enums must support `phenotype` or request explicit
existing filters. Searching a term does not infer disease relationships from text.
The existing quality dashboard remains scoped to its documented original records;
phenotype coverage is not silently included. Graph projection, phenotype hierarchies,
frequency/onset modeling, ontology mapping and real HPO ingestion are future work.

## Migration and deployment

Additive migration `20261111_0011` creates `phenotypes` and `disease_phenotypes`,
indexes, identity/assertion uniqueness and qualifier/evidence checks. Foreign keys
restrict deletion of referenced diseases or phenotypes. Existing tables and data
are retained; new collections start empty. No synthetic test term or assertion is
loaded into the public instance.

Before rollout, back up the live database privately, restore and compare record
counts, test fresh migrations and upgrade the restored copy. Run all backend tests,
Alembic model comparison, Ruff/mypy and frontend test/format/lint/type/build checks.
Retain tagged previous backend/frontend images before building new ones. Update
through the established VPS/Compose wrapper, then check public HTTPS, empty phenotype
catalogue/search, existing search/data quality, original record totals and blocked
writes. Application rollback uses the old images with the additive schema retained;
never reset or downgrade the live database as part of this release.

Release validation passed 174 backend and 46 frontend tests with the checks above.
The restored live backup upgraded to the new head with the original three genes,
three proteins, 128 transcripts and six evidenced identities preserved; phenotype
collections were empty and original TP53 search still returned 42 stored records.

For application rollback, override only backend/frontend images and retain the
0.14 migration service, which recognizes the new Alembic revision. An older
migration image cannot interpret revision 20261111_0011. The retained 0.13 backend
was also smoke-tested against the upgraded clone and successfully read the original
TP53 search results.

The deployed 0.14 application was verified over public HTTPS: the phenotype
catalogue and search were correctly empty, invalid pagination returned 422, missing
parents returned 404, the new SPA bundle loaded and public POST remained blocked.
The active migration head is 20261111_0011. Original starter record totals, TP53
search and the existing quality review remained available.
