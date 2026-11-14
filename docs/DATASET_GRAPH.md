# Dataset citation relationships and graph navigation — 0.19.0

This release extends long-term Phase 12 (Knowledge Graph Core), with existing
Phase 13 navigation, to GEO datasets and their explicitly reported publications.
It does not complete those roadmap phases or add inferred biological relationships.

## Source contract

`Dataset.publication_pmids` contains the citation identifiers supplied by GEO.
The resolver matches those strings exactly against `Publication.pubmed_id` in the
local database. Titles, abstracts, keywords, organisms and DOI similarity do not
create links. Missing local publications are returned as `missing_pmids`; the
resolver performs no network requests and does not create publication records.
Only dataset records with repository GEO and source `NCBI GEO` are eligible.
Administrative data creation remains a trusted operation, not independent source
verification.

The typed assertion is directed **dataset → cites → publication**. It means GEO
reported a citation for the Series, not that BKP independently verified use of
all samples or established a disease, causal, clinical or gene association.

Each `dataset_publications` row retains dataset/publication foreign keys, the
reported PMID, source accession/URL, metadata retrieval time, source record date,
structured-metadata evidence and creation time. Identity is unique per local
dataset/publication pair. Foreign keys restrict deletion. Repeated resolution
creates no duplicate; existing assertions retain their first observed provenance.

## Current metadata and first observed references

Dataset metadata refreshes continue to replace the current source PMID list.
Previously resolved citation assertions remain as first observed references if
later source metadata remove a PMID. Relationship panels and graph inspection
state this explicitly and show the original source record date. These links are
not a claim of current source membership. Re-resolution reports `existing` only
for references also present in the current source list.

This is a small assertion record, not full data versioning: withdrawn references
are not automatically marked/retracted, no complete source payload archive is
stored and no chronology of all source changes is reconstructed. The provider
update date is not a release/version identifier. Retrieval and assertion creation
are separate timestamps.

## API and operations

- `POST /api/v1/datasets/{id}/resolve-publications` requires the administrator
  token. It has no request payload and resolves only currently stored PMIDs.
- `GET /api/v1/relationships/dataset/{id}` and the existing publication direction
  return paginated incident assertions.
- `GET /api/v1/graph/dataset/{id}` supports the existing depth/node/edge/time
  budgets, entity filters and `relationship_type=dataset_publication`.
- Dataset detail links to the graph; graph nodes link back to dataset detail.
  Publication detail uses its existing relationship panel for reverse navigation.

From the backend working directory:

```sh
python -m app.cli import-publication 18297132
python -m app.cli resolve-dataset-publications GSE10072
```

The first command is an explicit, separate PubMed import. The second uses only
local records. The PubMed importer may create additional gene links only if its
structured ELink response matches genes already stored; dataset resolution itself
creates no gene links. Neither deployment nor ordinary web reads resolve links.
No periodic jobs, raw-data downloads or automatic bulk literature imports exist.

The resolver locks the dataset row, then matching publication rows in ID order,
and commits one transaction. Dataset refresh uses the same dataset lock. Unique
constraints protect duplicate identity; failures do not leave a partial batch.

## Migration and rollback

Migration `20261112_0016` adds a new table and indexes; it changes no existing
biological record. Downgrade refuses to discard stored citation assertions.
Before rollout, restore the private backup, upgrade the clone and verify the
previous backend against the additive schema. An application rollback retains
this schema and uses the retained images; do not run an older Alembic migration
service against a revision it does not know. Do not reset the live database.

## Public starter example

[GEO GSE10072](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE10072)
reports [PMID 18297132](https://pubmed.ncbi.nlm.nih.gov/18297132/). These source
identifiers, rather than title similarity, justify the local citation assertion.
See DATA_STATUS.md for the actual completed import and deployment verification.
