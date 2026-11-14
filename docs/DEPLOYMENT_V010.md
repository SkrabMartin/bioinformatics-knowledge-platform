# Release 0.10.0 and initial real data

The existing authorized temporary student preview at https://bkp.skrabana.com was
updated through the VPS scripts/bkp-preview.sh wrapper, preserving autostart and
the public read-only proxy. No DNS, Security Groups or Webglobe change was needed.

## Data

At the user's request, a small real starter set was imported through the existing
NCBI/UniProt adapters: TP53, BRCA1 and PINK1 genes and proteins P04637, P38398 and
Q9BXM7. The user supplied the required NCBI contact, saved only in private local
configuration. A private database backup was taken before the first real import.

Public API checks confirmed three genes, three proteins, NCBI/UniProt provenance,
TP53 reference placements and its explicit P04637 link. See DATA_STATUS.md.
Periodic synchronization is not enabled. Transcript records remain empty; they
require verified existing Ensembl gene mappings and successful provider responses.

## Verification and update

117 backend and 36 frontend tests passed with lint, formatting, typing and production
build checks. All nine migrations replayed on disposable PostgreSQL 17 with no
model/schema differences. Live Ensembl metadata encountered provider errors; no
successful live transcript import is claimed.

A fresh private pg_dump of the now-populated 0.9 database was restored into a
disposable database. The copy was upgraded to 20261107_0009 and key entity, job,
alias and location counts matched the source. The live update added one independent
table, reused the DB container/volume and preserved these verified real-data counts.

    /home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh build
    /home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh up -d --no-build --wait --wait-timeout 120

Live checks passed for public HTTPS, the new transcript SPA route and bundle,
API catalogue, gene/protein records and TP53 detail. All app services are healthy,
the migration exited 0 and head is 20261107_0009. Public writes still return 403.
The private contact was verified absent from the browser bundle.

## Rollback artifact repair

The original 0.9 frontend image/content was unavailable in Docker's image store;
tagging and container commit both failed. A shell sequencing error allowed the
application update to proceed after that image retention error, before a fallback
frontend image was ready. The database backup had already been restored/upgraded
successfully. This was corrected by rebuilding the 0.9 static frontend from source
commit 2e625f1, starting it without a host port and verifying its old bundle/assets.

The retained 0.9 backend image also passed its runtime version check. The frontend
fallback is a verified rebuild of the prior source, not a claim of a byte-identical
original image. The live 0.10 application and real data remained healthy.
Private artifacts: backups/v010-deploy-manifest.json and v09-rollback.compose.json.
The dump, checksums and source archive are excluded from Git/build contexts.

Application rollback, if needed:

    /home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh -f /home/martin_skrabana/projects/BKP/backups/v09-rollback.compose.json up -d --no-build --no-deps --wait backend frontend

Keep the independent transcript table and data backup. Do not run a destructive
downgrade or delete volumes. The artifact smoke checks are not a full live rollback,
external interactive browser test or VM reboot test. Local backups do not replace
an off-site backup policy.
