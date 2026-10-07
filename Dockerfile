# syntax=docker/dockerfile:1
#
# Render-specific: its Docker builder reads a literal `Dockerfile` at the
# repo root regardless of configured dockerfilePath/dockerContext (every
# attempt to point it at backend/Dockerfile with a backend/ build context
# failed identically: "open Dockerfile: no such file or directory"). This
# mirrors backend/Dockerfile (used for the GCP deploy, context=backend/)
# with COPY paths adjusted for a repo-root build context instead.
FROM python:3.12-slim

# psycopg[binary] ships its own libpq, so no postgres dev headers are needed.
# Playwright's Chromium (used for PDF report rendering) needs its browser +
# OS-level deps installed explicitly.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/sample_file ./sample_file

# Render (like Cloud Run) injects PORT.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
