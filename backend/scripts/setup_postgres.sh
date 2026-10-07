#!/usr/bin/env bash
# Provision a PostgreSQL database + role for the NCEP backend.
# Run once (needs postgres superuser access):
#
#   sudo -u postgres bash backend/scripts/setup_postgres.sh
#
# Override defaults via env vars: PG_DB, PG_USER, PG_PASSWORD
set -euo pipefail

PG_DB="${PG_DB:-ncep}"
PG_USER="${PG_USER:-ncep}"
PG_PASSWORD="${PG_PASSWORD:-ncep_password}"

psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${PG_USER}') THEN
      CREATE ROLE ${PG_USER} LOGIN PASSWORD '${PG_PASSWORD}';
   END IF;
END
\$\$;

SELECT 'CREATE DATABASE ${PG_DB} OWNER ${PG_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${PG_DB}')\gexec

GRANT ALL PRIVILEGES ON DATABASE ${PG_DB} TO ${PG_USER};
SQL

# Ensure schema privileges (PG 15+ locks down public schema by default)
psql -v ON_ERROR_STOP=1 -d "${PG_DB}" <<SQL
GRANT ALL ON SCHEMA public TO ${PG_USER};
ALTER SCHEMA public OWNER TO ${PG_USER};
SQL

echo "✓ Database '${PG_DB}' and role '${PG_USER}' ready."
echo "  Set in backend/.env:"
echo "  DATABASE_URL=postgresql+psycopg://${PG_USER}:${PG_PASSWORD}@localhost:5432/${PG_DB}"
