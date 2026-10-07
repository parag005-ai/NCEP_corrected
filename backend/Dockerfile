# syntax=docker/dockerfile:1
FROM python:3.12-slim

# psycopg[binary] ships its own libpq, so no postgres dev headers are needed.
# Playwright's Chromium (used for PDF report rendering) needs its browser +
# OS-level deps installed explicitly.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY sample_file ./sample_file

# Cloud Run injects PORT; default kept for local `docker run`.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
