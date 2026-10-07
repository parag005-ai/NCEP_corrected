#!/usr/bin/env bash
# Loads the app's built-in demo dataset (app/seed.py) into the deployed
# Cloud SQL database via a one-off Cloud Run Job -- same pattern as the
# migrate job. Idempotent: seed_db() no-ops if the users table isn't empty.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ./config.sh

gcloud config set project "$PROJECT_ID" >/dev/null
INSTANCE_CONNECTION_NAME="$(gcloud sql instances describe "$SQL_INSTANCE" --format='value(connectionName)')"

SEED_JOB="ncep-seed"

if gcloud run jobs describe "$SEED_JOB" --region="$REGION" >/dev/null 2>&1; then
  gcloud run jobs update "$SEED_JOB" \
    --image="$BACKEND_IMAGE" \
    --region="$REGION" \
    --set-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
    --set-secrets="DATABASE_URL=${DB_URL_SECRET_NAME}:latest" \
    --command="python" \
    --args="-m,app.seed"
else
  gcloud run jobs create "$SEED_JOB" \
    --image="$BACKEND_IMAGE" \
    --region="$REGION" \
    --set-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
    --set-secrets="DATABASE_URL=${DB_URL_SECRET_NAME}:latest" \
    --command="python" \
    --args="-m,app.seed"
fi
gcloud run jobs execute "$SEED_JOB" --region="$REGION" --wait

cat <<'EOF'

Demo data loaded. Every seeded account logs in with password: password

  superadmin@ncep.demo    (superadmin)
  admin@ncep.demo         (admin, City General Hospital)
  neha.sharma@ncep.demo   (admin, National Cardiology Institute)
  doctor@ncep.demo        (doctor, Dr. Meera Shah)
  patient@ncep.demo       (patient, Anaya Rao)

This is DEMO_PASSWORD (backend default "password"), shared by every seeded
account -- fine for trying the app, not for a real deployment. Change it via
the JWT_SECRET-style flow: set a real DEMO_PASSWORD secret and redeploy, or
just change individual passwords once logged in.
EOF
