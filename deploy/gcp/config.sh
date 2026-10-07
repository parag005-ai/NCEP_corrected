#!/usr/bin/env bash
# Shared config for deploy/gcp/*.sh. Edit here, then run the numbered
# scripts in order: 01-infra-setup.sh, 02-deploy-backend.sh, 03-deploy-frontend.sh.
set -euo pipefail

# Must be globally unique across all of GCP. If `gcloud projects create`
# rejects it as taken, change this and re-run 01-infra-setup.sh.
PROJECT_ID="${PROJECT_ID:-ncep-platform}"
PROJECT_NAME="NCEP Clinical Platform"
BILLING_ACCOUNT_ID="${BILLING_ACCOUNT_ID:-012383-C62D06-38CAF6}"
REGION="us-central1"

AR_REPO="ncep-repo"
BACKEND_IMAGE_NAME="ncep-backend"
FRONTEND_IMAGE_NAME="ncep-frontend"

BACKEND_SERVICE="ncep-backend"
FRONTEND_SERVICE="ncep-frontend"
MIGRATE_JOB="ncep-migrate"

SQL_INSTANCE="ncep-db"
SQL_TIER="db-f1-micro"
SQL_DB_NAME="ncep"
SQL_DB_USER="ncep_app"

GCS_BUCKET="${PROJECT_ID}-storage"

JWT_SECRET_NAME="ncep-jwt-secret"
DB_URL_SECRET_NAME="ncep-database-url"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/NCEPfrontend"
DEPLOY_DIR="${REPO_ROOT}/deploy/gcp"

BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${BACKEND_IMAGE_NAME}:latest"
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${FRONTEND_IMAGE_NAME}:latest"
