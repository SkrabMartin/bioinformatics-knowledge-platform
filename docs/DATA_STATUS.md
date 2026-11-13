# Initial real data and refresh behavior

A bounded starter import was run explicitly after the user requested actual data.
The monitored NCBI contact was configured only in private local configuration.
No contact address, credential or database dump belongs in Git.

## Imported source records

| Kind | Identifier | Source |
|---|---|---|
| Gene | BRCA1 / 672 | [NCBI Gene](https://www.ncbi.nlm.nih.gov/gene/672) |
| Gene | PINK1 / 65018 | [NCBI Gene](https://www.ncbi.nlm.nih.gov/gene/65018) |
| Gene | TP53 / 7157 | [NCBI Gene](https://www.ncbi.nlm.nih.gov/gene/7157) |
| Protein | P04637 | [UniProt](https://www.uniprot.org/uniprotkb/P04637/entry) |
| Protein | P38398 | [UniProt](https://www.uniprot.org/uniprotkb/P38398/entry) |
| Protein | Q9BXM7 | [UniProt](https://www.uniprot.org/uniprotkb/Q9BXM7/entry) |

The public API verified three genes, three proteins, source provenance, reference
placements and the TP53–P04637 encoding link. Protein reimport matched existing
genes through imported stable identifiers. No artificial gene/protein records were
copied from test databases. Other biological collections require their own sourced
imports; this starter set is not a representative whole-genome dataset.

## When data load

Data are loaded when an explicit CLI import runs or when a submitted import job
is processed by the optional worker. Deploying a schema or starting the website
does not itself populate biological data.

This initial import has completed and is visible at /genes and /proteins.
Periodic refresh/scheduling is not enabled. More records can be submitted through
the protected job API or host CLI, then processed by the existing imports worker.
The NCBI contact is now forwarded to the active backend/worker from .env.preview.
See IMPORT_JOBS.md for queue and retry behavior.

## Transcript import — 2026-11-11 / release 0.11.0

The public instance now also contains 128 real Ensembl transcript annotations:

| Gene | Source-backed Ensembl gene | Imported transcripts |
|---|---|---:|
| TP53 | ENSG00000141510 | 40 |
| BRCA1 | ENSG00000012048 | 59 |
| PINK1 | ENSG00000158828 | 29 |

UniProt protein reimports supplied explicit GeneID and Ensembl GeneId mapping
assertions for the three existing genes. The registry contains six primary
identities with provider evidence. Gene record provenance remains NCBI; mapping
evidence identifies its actual UniProt source separately. Ensembl imports validated
species, parent, assembly and release before committing each gene's transcripts.

The sequence was first checked on an upgraded, restored copy of the live database,
then executed through the host CLI in the deployed Compose backend. Public HTTPS
checks verified catalogue totals, each gene's transcript count, stable/observed-version
identifier resolution and rejection of unknown versions. Original three genes,
three proteins and one organism remain. Public write methods remain blocked.

This is a bounded starter set, not whole-genome coverage or an automatic data feed.
Transcript metadata are available at /transcripts and on gene detail pages.
See [transcripts](TRANSCRIPTS.md) and [identifier evidence](GENE_IDENTIFIERS.md).

## Metadata review

Release 0.12 adds the read-only [data quality review](DATA_QUALITY.md) at
`/data-quality`. It checks the stored starter records and their identifier metadata;
it does not load additional biological records or enable scheduled updates.

## Phenotype availability

Release 0.14 introduces phenotype terms and sourced disease assertions. Those
collections start empty; no synthetic examples or unverified biological claims are
loaded during deployment. The existing real starter records remain the source of
public gene/protein/transcript data. See [phenotype operations](PHENOTYPES.md).

## Variant placement availability

Release 0.15 introduces source-supplied assembly/sequence/allele observations for
existing variants. The new table starts empty and no synthetic variants or inferred
coordinates are loaded. Real variant/placement imports require their own source
adapter or administrator-supplied, traceable observations.
See [placement operations](VARIANT_PLACEMENTS.md).

## Cellular component availability

Release 0.16 adds the third GO aspect and direct protein annotations. The CC
catalogue and annotation table start empty; deployment does not copy synthetic
terms or infer localizations for the starter proteins. Source ingestion remains
explicit future work. See [cellular components](CELLULAR_COMPONENTS.md).

## Literature starter records — 2026-11-12 / 0.17.0

Two real PubMed citations were explicitly imported through the existing adapter
following staged validation on a restored live database:

| PMID | Source | Stored keywords |
|---|---|---:|
| 40524430 | [PubMed](https://pubmed.ncbi.nlm.nih.gov/40524430/) | 5 |
| 39688918 | [PubMed](https://pubmed.ncbi.nlm.nih.gov/39688918/) | 5 |

Citation metadata, available source abstracts and keywords are visible in the
publication catalogue. Keyword search is available in both the catalogue and
unified search. These imports created zero gene links because their structured
ELink responses supplied none for local records. No links were inferred from titles
or keywords. No variant or publication–variant assertions were created.

The original three genes, three proteins and 128 transcripts remain available.
This is a bounded starter sample, not an exhaustive gene literature bibliography;
scheduled citation refresh and automatic variant linkage remain disabled.
See [literature metadata](LITERATURE_METADATA.md).

## Dataset discovery — 2026-11-12 / release 0.18.0

The public instance contains one real GEO Series metadata record:
[GSE10072](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE10072).
Its source reports 107 repository sample records, platform GPL96, Homo sapiens
(taxonomy 9606), expression profiling by array and external publication PMID
18297132. Sample records are not necessarily patients or independent observations.
The provider last-update date is 2018-08-10; retrieval time is stored separately.

This was an explicit, bounded metadata import, first verified on a restored copy
of the database. No experimental files were downloaded and no local organism,
disease, gene or publication relationships were inferred. The existing two
imported publications remain unchanged; PMID 18297132 is an external source
reference only. Scheduling is not enabled for dataset imports. See DATASETS.md.

Public HTTPS checks verified dataset browse/detail, exact-accession unified
search, suggestions, input bounds and blocked public writes. Existing totals
remain three genes, three proteins, 128 transcripts and two publications.

## Dataset citation graph — 2026-11-12 / release 0.19.0

The source-reported citation [PMID 18297132](https://pubmed.ncbi.nlm.nih.gov/18297132/)
was explicitly imported, then resolved locally from GSE10072's GEO metadata.
The public instance now has three PubMed publications and one dataset citation
assertion. No gene links were added by this import. Repeated citation resolution
returned one existing assertion and created no duplicate.

The directed GSE10072 → cites → publication edge preserves the GEO accession,
URL, retrieval time and source record date 2018-08-10. Dataset and publication
detail expose this link in both directions, with graph navigation and evidence
inspection. First observed citations remain if later source metadata change;
they are not a guarantee of current source membership or a biological conclusion.

Public HTTPS checks passed relationship reads, both graph roots, relationship
filters, node/depth bounds, source provenance, SPA assets and blocked resolution
writes. All pre-existing table counts were preserved apart from the explicit
additional publication: three genes, three proteins, 128 transcripts and one
dataset remain. The two previous PubMed records remain present.
See DATASET_GRAPH.md for contracts and limitations.

## Visible graph export — 2026-11-13 / release 0.20.0

The graph explorer now downloads the visible graph as JSON/GraphML with complete
source assertions and partial-view metadata. No records were imported or changed
for this release: three genes, three proteins, 128 transcripts, three publications,
one dataset and one dataset citation remain. All checked table counts matched
the pre-deployment backup. Schema remains 20261112_0016.

The application exporter serialized the real GSE10072 citation graph to both
formats; a separate XML parser confirmed its two nodes, one edge and provenance.
Public HTTPS checks verified updated frontend/chunk assets, existing reads, graph
filters/bounds and blocked writes. This is not a claim of a browser download E2E
test or universal external graph-tool compatibility. See GRAPH_EXPORT.md.
