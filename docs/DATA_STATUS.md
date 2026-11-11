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
