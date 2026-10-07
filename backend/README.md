# NCEP Backend API

FastAPI + SQLAlchemy + Alembic backend for the NCEP (Neuro Cardiac Electrophysiology Platform)
frontend (`../NCEPfrontend`). Every response is shaped to match the frontend TypeScript
types in `NCEPfrontend/src/types/index.ts` exactly (camelCase keys, same IDs), so it is a
drop-in replacement for the old localStorage mock layer.

## Stack

- **FastAPI** — REST API
- **SQLAlchemy 2.0** — ORM
- **Alembic** — schema migrations
- **PyJWT** + stdlib pbkdf2 — auth (no native crypto build deps)
- **PostgreSQL** (default `DATABASE_URL`); SQLite fallback for zero-setup

## Quick start (PostgreSQL)

1. **Provision the database** (once, needs postgres superuser):

   ```bash
   sudo -u postgres bash backend/scripts/setup_postgres.sh
   # → database "ncep", role "ncep" / "ncep_password"
   ```

2. **Run everything:**

   ```bash
   cd backend
   ./run.sh          # venv, install, migrate, seed, ingest sample SAECG, serve :8000
   ```

   Or manually:

   ```bash
   python3.12 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env          # DATABASE_URL already points at Postgres
   alembic upgrade head          # apply migrations
   python -m app.seed            # load demo data (orgs/users/patients/reports/...)
   python -m app.seed_sample     # ingest the real 15-lead SAECG sample for pat-001
   uvicorn app.main:app --reload --port 8000
   ```

To use SQLite instead, set `DATABASE_URL=sqlite:///./ncep.db` in `.env`.

Interactive docs: http://localhost:8000/docs

## Demo accounts

All seeded accounts use the password **`password`** (set via `DEMO_PASSWORD`).

| Role       | Email                  |
|------------|------------------------|
| Patient    | `patient@ncep.demo`    |
| Doctor     | `doctor@ncep.demo`     |
| Admin      | `admin@ncep.demo`      |
| Superadmin | `superadmin@ncep.demo` |

## Auth

JWT bearer tokens. `POST /api/auth/login` returns `{ token, session }`; send the token as
`Authorization: Bearer <token>` on every other request.

## Endpoints

| Method | Path                              | Notes |
|--------|-----------------------------------|-------|
| POST   | `/api/auth/login`                 | → `{ token, session }` |
| GET    | `/api/auth/me`                    | current session |
| POST   | `/api/auth/logout`                | stateless (client drops token) |
| GET/POST | `/api/users`                    | `?organisationId=&role=` |
| GET/PATCH | `/api/users/{id}`              | |
| GET/POST | `/api/organisations`            | |
| GET/PATCH | `/api/organisations/{id}`      | |
| GET/POST | `/api/doctors`                  | `?organisationId=` |
| GET/PATCH | `/api/doctors/{id}`            | |
| GET/POST | `/api/patients`                 | `?organisationId=&assignedDoctorId=&status=` |
| GET/PATCH/DELETE | `/api/patients/{id}`    | |
| GET/POST | `/api/ecg-records`              | `?patientId=&doctorId=&organisationId=` |
| POST   | `/api/ecg-records/upload`         | multipart: `file` (waveform CSV) + optional `ecgMetadata`/`patientMetadata` JSON |
| GET    | `/api/ecg-records/{id}/waveform`  | downsampled samples: `?leads=I,II,V1&maxPoints=2000` |
| GET/PATCH | `/api/ecg-records/{id}`        | |
| GET/POST | `/api/reports`                  | `?patientId=&doctorId=&organisationId=&status=&sharedWithPatient=` |
| GET/PATCH | `/api/reports/{id}`            | |
| POST   | `/api/reports/{id}/approve`       | sets status=Approved |
| POST   | `/api/reports/{id}/share`         | sets status=Shared, sharedWithPatient=true |
| GET/POST | `/api/audit-logs`               | `?organisationId=&eventType=&limit=` |
| GET    | `/api/health`                     | liveness |

## Wiring the frontend

A ready-to-use typed client lives at `NCEPfrontend/src/lib/api/index.ts` with the same
function surface as the old mock DB. To connect the frontend:

1. `cp NCEPfrontend/.env.local.example NCEPfrontend/.env.local` (points at `:8000`).
2. In pages, replace mock imports, e.g.:
   ```ts
   // before
   import { getPatients } from "@/lib/mock-data/db";
   const rows = getPatients().filter(p => p.assignedDoctorId === session.doctorId);
   // after
   import { patients } from "@/lib/api";
   const rows = await patients.list({ assignedDoctorId: session.doctorId });
   ```
3. Point `AuthProvider`/`mock-auth` login at `api.auth.login(email, password)` — it returns the
   same `Session` shape and stores the JWT in `localStorage` under `ncep_token`.

## Migrations

```bash
alembic revision --autogenerate -m "describe change"   # after editing app/models.py
alembic upgrade head
alembic downgrade -1
```

## Switching to Postgres

Set in `.env`:

```
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/ncep
```

Install the driver (`pip install "psycopg[binary]"`), then `alembic upgrade head` and
`python -m app.seed`.
