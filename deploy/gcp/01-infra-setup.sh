#!/usr/bin/env bash
# One-time infra setup: GCP project, APIs, Artifact Registry, Cloud SQL,
# GCS bucket, and Secret Manager entries. Safe to re-run -- each step checks
# whether its resource already exists first.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ./config.sh

echo "== 1/7 Project =="
if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME"
else
  echo "Project $PROJECT_ID already exists, reusing."
fi
gcloud config set project "$PROJECT_ID" >/dev/null

echo "== 2/7 Billing =="
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT_ID"

echo "== 3/7 Enable APIs =="
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  --project="$PROJECT_ID"

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

echo "== 4/7 Artifact Registry =="
if ! gcloud artifacts repositories describe "$AR_REPO" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$AR_REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="NCEP backend/frontend images"
else
  echo "Repo $AR_REPO already exists, reusing."
fi
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CLOUDBUILD_SA}" --role="roles/artifactregistry.writer" \
  --condition=None >/dev/null

echo "== 5/7 Cloud SQL for PostgreSQL ($SQL_TIER, zonal, no HA) =="
if ! gcloud sql instances describe "$SQL_INSTANCE" >/dev/null 2>&1; then
  gcloud sql instances create "$SQL_INSTANCE" \
    --database-version=POSTGRES_16 \
    --edition=enterprise \
    --tier="$SQL_TIER" \
    --region="$REGION" \
    --availability-type=zonal \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup-start-time=03:00
else
  echo "Instance $SQL_INSTANCE already exists, reusing."
fi

if ! gcloud sql databases describe "$SQL_DB_NAME" --instance="$SQL_INSTANCE" >/dev/null 2>&1; then
  gcloud sql databases create "$SQL_DB_NAME" --instance="$SQL_INSTANCE"
fi

DB_PASSWORD="$(openssl rand -base64 24)"
if gcloud sql users list --instance="$SQL_INSTANCE" --format="value(name)" | grep -qx "$SQL_DB_USER"; then
  gcloud sql users set-password "$SQL_DB_USER" --instance="$SQL_INSTANCE" --password="$DB_PASSWORD"
else
  gcloud sql users create "$SQL_DB_USER" --instance="$SQL_INSTANCE" --password="$DB_PASSWORD"
fi

INSTANCE_CONNECTION_NAME="$(gcloud sql instances describe "$SQL_INSTANCE" --format='value(connectionName)')"
DATABASE_URL="postgresql+psycopg://${SQL_DB_USER}:${DB_PASSWORD}@/${SQL_DB_NAME}?host=/cloudsql/${INSTANCE_CONNECTION_NAME}"

echo "== 6/7 GCS bucket for ECG uploads/reports =="
if ! gcloud storage buckets describe "gs://${GCS_BUCKET}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${GCS_BUCKET}" --location="$REGION" --uniform-bucket-level-access
else
  echo "Bucket gs://${GCS_BUCKET} already exists, reusing."
fi
gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET}" \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/storage.objectAdmin" >/dev/null

echo "== 7/7 Secret Manager =="
upsert_secret() {
  local name="$1" value="$2"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- >/dev/null
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- >/dev/null
  fi
  gcloud secrets add-iam-policy-binding "$name" \
    --member="serviceAccount:${RUNTIME_SA}" --role="roles/secretmanager.secretAccessor" >/dev/null
}
upsert_secret "$JWT_SECRET_NAME" "$(openssl rand -hex 32)"
upsert_secret "$DB_URL_SECRET_NAME" "$DATABASE_URL"

# Runtime SA needs this to use the Cloud SQL Auth Proxy Cloud Run mounts automatically.
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/cloudsql.client" \
  --condition=None >/dev/null

cat <<EOF

Infra ready.
  Project:            $PROJECT_ID
  Cloud SQL instance:  $INSTANCE_CONNECTION_NAME
  GCS bucket:          gs://${GCS_BUCKET}
  Secrets:             $JWT_SECRET_NAME, $DB_URL_SECRET_NAME

Next: ./02-deploy-backend.sh
EOF
