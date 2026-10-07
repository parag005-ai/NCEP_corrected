#!/usr/bin/env bash
# One-shot: set up env, migrate, seed, and run the API.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3.12 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

[ -f .env ] || cp .env.example .env

alembic upgrade head
python -m app.seed
python -m app.seed_sample   # ingest the real sample SAECG bundle for the demo

exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
