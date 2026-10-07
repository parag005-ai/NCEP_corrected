#!/usr/bin/env bash
# Builds the backend image (via Cloud Build -- no local Docker needed), runs
# Alembic migrations as a one-off Cloud Run Job, then deploys the backend
# Cloud Run service. Re-run any time backend code changes.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ./config.sh

gcloud config set project "$PROJECT_ID" >/dev/null
INSTANCE_CONNECTION_NAME="$(gcloud sql instances describe "$SQL_INSTANCE" --format='value(connectionName)')"

echo "== Build & push backend image =="
gcloud builds submit --tag "$BACKEND_IMAGE" "$BACKEND_DIR"

echo "== Run Alembic migrations (Cloud Run Job) =="
if gcloud run jobs describe "$MIGRATE_JOB" --region="$REGION" >/dev/null 2>&1; then
  gcloud run jobs update "$MIGRATE_JOB" \
    --image="$BACKEND_IMAGE" \
    --region="$REGION" \
    --set-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
    --set-secrets="DATABASE_URL=${DB_URL_SECRET_NAME}:latest" \
    --command="alembic" \
    --args="upgrade,head"
else
  gcloud run jobs create "$MIGRATE_JOB" \
    --image="$BACKEND_IMAGE" \
    --region="$REGION" \
    --set-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
    --set-secrets="DATABASE_URL=${DB_URL_SECRET_NAME}:latest" \
    --command="alembic" \
    --args="upgrade,head"
fi
gcloud run jobs execute "$MIGRATE_JOB" --region="$REGION" --wait

echo "== Deploy backend Cloud Run service =="
# CORS_ORIGINS always includes localhost for local dev; once
# 03-deploy-frontend.sh has run at least once it records the frontend's URL
# in .frontend-url, which subsequent backend redeploys pick up here too.
CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
if [ -f "${DEPLOY_DIR}/.frontend-url" ]; then
  CORS_ORIGINS="${CORS_ORIGINS},$(cat "${DEPLOY_DIR}/.frontend-url")"
fi

# --no-cpu-throttling ("CPU always allocated"): report generation runs as a
# FastAPI BackgroundTask after the request that queued it has already
# returned, so it needs CPU outside a request's lifetime -- Cloud Run's
# default (CPU only while a request is in flight) stalls it almost to a
# halt, especially now that report generation does real signal-processing
# work (app/signal_processing/). This does mean the container is billed for
# CPU for its whole lifetime while running, not just while serving a
# request -- min-instances=0 still bounds that to when an instance is up.
gcloud run deploy "$BACKEND_SERVICE" \
  --image="$BACKEND_IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --execution-environment=gen2 \
  --allow-unauthenticated \
  --add-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
  --add-volume=name=ecg-storage,type=cloud-storage,bucket="$GCS_BUCKET" \
  --add-volume-mount=volume=ecg-storage,mount-path=/mnt/gcs \
  --set-secrets="DATABASE_URL=${DB_URL_SECRET_NAME}:latest,JWT_SECRET=${JWT_SECRET_NAME}:latest" \
  --set-env-vars="^;^APP_ENV=production;ECG_STORAGE_ROOT=/mnt/gcs/ecg_storage;ECG_UPLOAD_TEMP_DIR=/mnt/gcs/ecg_uploads;ECG_UPLOAD_STATUS_DIR=/mnt/gcs/ecg_upload_status;REPORT_STORAGE_ROOT=/mnt/gcs/report_storage;CORS_ORIGINS=${CORS_ORIGINS}" \
  --memory=2Gi \
  --cpu=2 \
  --no-cpu-throttling \
  --min-instances=0 \
  --max-instances=3 \
  --timeout=120

BACKEND_URL="$(gcloud run services describe "$BACKEND_SERVICE" --region="$REGION" --format='value(status.url)')"
echo "$BACKEND_URL" > .backend-url

cat <<EOF

Backend deployed: $BACKEND_URL
Health check:     curl ${BACKEND_URL}/api/health

Next: ./03-deploy-frontend.sh
EOF
