# Deploying NCEP to Google Cloud

Deploys `backend/` and `NCEPfrontend/` as two Cloud Run services, backed by
Cloud SQL for PostgreSQL and a GCS bucket for ECG/report file storage.

## Prerequisites

- `gcloud` CLI authenticated (`gcloud auth login`) with a billing account available.
- No local Docker required -- images are built remotely via Cloud Build.

## One-time config

Edit [`config.sh`](config.sh) if you want a different project ID, region, or
resource names. `PROJECT_ID` must be globally unique; if `01-infra-setup.sh`
fails with "already exists", change it and re-run.

## Deploy order

```bash
cd deploy/gcp
./01-infra-setup.sh      # project, APIs, Artifact Registry, Cloud SQL, GCS bucket, secrets (~5-10 min, mostly Cloud SQL)
./02-deploy-backend.sh   # build, run Alembic migrations, deploy backend
./03-deploy-frontend.sh  # build (with backend URL baked in), deploy frontend, patch backend CORS
```

Each script is safe to re-run. After the first full run, re-run just
`02-deploy-backend.sh` or `03-deploy-frontend.sh` to ship code changes to
one side without touching infra.

## What gets created

| Resource | Name | Notes |
|---|---|---|
| GCP project | `ncep-platform` (edit in config.sh) | dedicated, billing-linked |
| Cloud SQL instance | `ncep-db` | `db-f1-micro`, zonal (no HA), daily backups |
| Cloud SQL database/user | `ncep` / `ncep_app` | password generated with `openssl rand`, stored in Secret Manager |
| GCS bucket | `<project-id>-storage` | mounted at `/mnt/gcs` in the backend container via Cloud Run's native volume mount (GCS FUSE) |
| Artifact Registry repo | `ncep-repo` | Docker images |
| Secret Manager | `ncep-jwt-secret`, `ncep-database-url` | injected into Cloud Run as env vars |
| Cloud Run service | `ncep-backend` | FastAPI, gen2 execution env, Cloud SQL Auth Proxy attached |
| Cloud Run service | `ncep-frontend` | Next.js standalone server |
| Cloud Run job | `ncep-migrate` | runs `alembic upgrade head`, executed once per backend deploy |

No seed data is loaded. The database starts empty (schema-only, via Alembic
migrations) -- `app/seed.py` / `app/seed_sample.py` are dev-only scripts and
are **not** run against the cloud database, since they create demo accounts
sharing one password. Create your first real admin some other way (e.g. a
one-off `gcloud run jobs execute` running a small script, or a direct
`psql` insert) before the app is usable.

## Costs (rough, us-central1)

- Cloud SQL `db-f1-micro`: ~$10-15/month, runs 24/7 regardless of traffic (dominant fixed cost).
- Cloud Run (both services): pay-per-request, `min-instances=0` means ~$0 when idle. The backend runs with `--no-cpu-throttling` (needed so report generation's background task, including signal processing, actually gets CPU after its triggering request returns) -- this bills CPU for the container's whole running lifetime rather than just active-request time, but only while an instance is actually up.
- GCS bucket + Artifact Registry storage: a few cents/month at demo scale.

## Known limitations

- **GCS FUSE is not a full POSIX filesystem.** Fine for this app's simple
  write-then-read file pattern, but not a place to add heavy concurrent
  writes to the same file without further work.
- **No HA** on the Cloud SQL instance -- a zone outage causes backend
  downtime. Upgrade later with `gcloud sql instances patch ncep-db
  --availability-type=regional` (no data loss, brief downtime during the
  change).
- **Cold starts**: first request after idle is slow, especially on the
  backend (Chromium takes a moment to start for PDF report rendering). Fix
  with `gcloud run services update ncep-backend --region us-central1
  --min-instances=1` (small ongoing cost, no rebuild needed).

## Tearing everything down

```bash
gcloud projects delete ncep-platform
```

Deletes every resource created above in one shot (project deletion has a
~30 day recovery grace period during which billing stops but the project ID
stays reserved).
