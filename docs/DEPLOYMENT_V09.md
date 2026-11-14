# Release 0.9.0 deployment

The existing user-authorized temporary student preview at bkp.skrabana.com remains
the deployment target. This release follows long-term roadmap Phase 2, independent
of the historical implementation milestone numbering.

## Preparation

- 95 backend and 33 frontend tests passed, including all prior features.
- Ruff, mypy, ESLint, Prettier, TypeScript and production build passed.
- All eight migrations replayed on disposable PostgreSQL 17; Alembic found no
  model/schema differences.
- Active 0.8 DB backed up in private backups/ with SHA-256. Restored revision and
  key entity/job counts matched. The restored copy was then successfully migrated
  from 20261107_0007 to 20261107_0008, with those counts preserved.
- Prior runtime images retained in private backups/v09-deploy-manifest.json.
- Private backup directories are excluded from Git and Docker build context.

## Deployment and rollback

The existing VPS scripts/bkp-preview.sh wrapper preserves autostart:

```bash
/home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh build
/home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh up -d --no-build --wait --wait-timeout 120
```

The additive migration only creates source context tables/indexes. No legacy
gene columns or records are rewritten. No fixtures or real biological imports
are run. The public proxy, DNS, Security Groups and main Webglobe website do not
need modification.

For application rollback to retained 0.8 images:

```bash
/home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh \
  -f /home/martin_skrabana/projects/BKP/backups/v08-rollback.compose.json \
  up -d --no-build --no-deps --wait backend frontend
```

Preserve the new independent tables and backup. No routine database restore or
destructive Alembic downgrade is needed for this compatible application rollback.
The private override and images exist only on this VM; they are not fresh-clone
artifacts. Local backup alone does not protect against loss of the VM.

## Observed result

Deployment completed successfully. The DB container was reused, all three running
services are healthy and migration exited 0 at 20261107_0008.
The live API reports 0.9.0 and its OpenAPI gene-detail schema contains the new
alias/placement fields. Public HTTPS, /about and /genes SPA routes, JS/CSS, search
and database API passed. The bundle contains the 0.9 gene-context label and uses
/api/v1 without localhost:8000. Previously captured entity/job counts match.
Public POST/PATCH/DELETE remain blocked with 403.

No test data were inserted into the public instance; an absent synthetic alias
still returns no results. These are server-side HTTPS checks, not a remote
interactive browser test or a VM reboot test.
