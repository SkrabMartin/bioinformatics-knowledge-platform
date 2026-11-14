# Phase 8 public preview update — 2026-11-07

The user explicitly requested that the GitHub changes also affect
https://bkp.skrabana.com. Existing VPS documentation confirms the previously
authorized **temporary student preview in a personal e-INFRA project**.
This update preserves that mode; it does not establish long-term production
approval, modify DNS/Security Groups or change the main Webglobe website.

## Deployment

Existing public Caddy → 127.0.0.1:8088 → BKP nginx → FastAPI/PostgreSQL.
The application update used the existing VPS wrapper, preserving its restart
override rather than replacing infrastructure configuration:

```bash
/home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh build
/home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh up -d --no-build --wait --wait-timeout 120
```

Before updating, the active DB was dumped in PostgreSQL custom format to the
ignored private BKP backups directory (0700 directory, 0600 files), with SHA-256.
The dump was restored successfully into a new DB on the disposable test container;
its revision was confirmed as Phase 7 head `20261023_0006`.
The old runtime images were tagged and retained. Local deployment metadata is in
`backups/phase8-deploy-manifest.json`; it and the dump are deliberately not in Git.
These local backups still require an independently approved off-site backup policy.

Compose recreated the application containers and the DB container while retaining
the original PostgreSQL volume. Migration `20261107_0007` succeeded. No database
reset, volume removal, fixtures or real scientific imports were performed.

## Observed result

- Backend version 0.8.0, Alembic head 20261107_0007.
- DB, backend and frontend healthy; migration service exited 0.
- Public HTTPS and ordinary domain resolution work from this VM with certificate
  verification; the existing VPS check-public.sh also passed.
- Home, /about and /genes SPA deep links, new JS/CSS assets, /api/health and six
  entity collections passed. Collections remain empty.
- Public bundle contains the Phase 8 / Tracked imports label and uses /api/v1,
  without localhost:8000 calls.
- POST/PATCH/DELETE remain blocked with 403. GET import-jobs fails closed with
  503 because the server administrator token remains intentionally unset.
- An empty-queue worker --once check in the backend exited successfully, without
  making provider requests. The continuous worker remains opt-in and stopped.
- 78 backend tests passed against disposable PostgreSQL, 30 frontend tests passed,
  lint/format/type checks and the production build passed.
- The complete seven-migration replay and Alembic model comparison passed.
- This is server-side HTTPS verification, not a test from another user's browser
  or a VM reboot test. Reload an already-open browser tab to receive the new bundle.

## Rollback

Private `backups/phase7-rollback.compose.json` points at retained pre-update images.
Since the migration only adds independent tables, Phase 7 application code remains
compatible with the new schema. If an application rollback is required:

```bash
/home/martin_skrabana/projects/VPS/scripts/bkp-preview.sh \
  -f /home/martin_skrabana/projects/BKP/backups/phase7-rollback.compose.json \
  up -d --no-build --no-deps --wait backend frontend
```

Check public HTTPS and DB reads afterward. This rollback does not delete the new
job tables, restore a database or run a destructive downgrade. Preserve the dump
and image tags. Restoring active data is a separate approved recovery operation.
The private manifest, images and backup are local operational artifacts; a future
fresh clone must not assume they exist.
