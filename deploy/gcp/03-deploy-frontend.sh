#!/usr/bin/env bash
# Reads the backend's live URL, builds the frontend image with it baked in
# as NEXT_PUBLIC_API_BASE_URL (Next.js inlines this at build time), deploys
# the frontend Cloud Run service, then patches the backend's CORS_ORIGINS to
# allow the frontend's real origin. Re-run any time frontend code changes.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ./config.sh

gcloud config set project "$PROJECT_ID" >/dev/null

if [ ! -f .backend-url ]; then
  echo "No .backend-url found -- run ./02-deploy-backend.sh first." >&2
  exit 1
fi
BACKEND_URL="$(cat .backend-url)"
API_BASE_URL="${BACKEND_URL}/api"

echo "== Build & push frontend image (API base: $API_BASE_URL) =="
gcloud builds submit "$FRONTEND_DIR" \
  --config=cloudbuild-frontend.yaml \
  --substitutions="_IMAGE=${FRONTEND_IMAGE},_API_BASE_URL=${API_BASE_URL}"

echo "== Deploy frontend Cloud Run service =="
gcloud run deploy "$FRONTEND_SERVICE" \
  --image="$FRONTEND_IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --timeout=60

FRONTEND_URL="$(gcloud run services describe "$FRONTEND_SERVICE" --region="$REGION" --format='value(status.url)')"
echo "$FRONTEND_URL" > .frontend-url

echo "== Patch backend CORS_ORIGINS to allow $FRONTEND_URL =="
gcloud run services update "$BACKEND_SERVICE" \
  --region="$REGION" \
  --update-env-vars="^;^CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,${FRONTEND_URL}"

cat <<EOF

Frontend deployed: $FRONTEND_URL
Backend:           $BACKEND_URL

Open $FRONTEND_URL in a browser to try the app.
EOF
