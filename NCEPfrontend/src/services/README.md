# NCEP service-layer contract

`src/services/` is the only browser-facing domain-data boundary. Pages must
import from `@/services`; they must not access domain `localStorage` or call
`fetch` against the backend directly.

## Configuration

Set `NEXT_PUBLIC_API_BASE_URL` to the backend's API root, including the
`/api` prefix every backend router is mounted under (e.g.
`http://localhost:8000/api`). A missing base URL raises a typed
`ServiceError` rather than falling back to any local data.

## Authentication and errors

The HTTP client uses `credentials: "include"`. `POST /auth/login` sets an
HttpOnly, `Secure`, `SameSite=None` session cookie (see
`backend/app/routers/auth.py`); the JWT itself is never present in a
JS-readable response body. `POST /auth/logout` clears it. The backend's CORS
configuration (`CORS_ORIGINS`) must list the frontend's exact origin(s) --
`allow_credentials` requires a concrete origin list, not a wildcard.

Every live response is validated at runtime before it reaches the UI. Failed
requests throw `ServiceError` with these useful fields:

- `code`: `network`, `unauthorized`, `forbidden`, `not_found`, `conflict`,
  `rate_limited`, `invalid_response`, and related categories.
- `status`: HTTP status when available.
- `retryable`: true for network, 429, and 5xx failures.

Callers may pass `{ signal }` as an optional final/options argument to cancel a
request when a page is unmounted.

## Endpoints

All successful list and entity responses are direct JSON values matching the
TypeScript types in `src/types/index.ts`; they are not wrapped in `{ data: ... }`.
Error responses are `{ "error": { "code": "...", "message": "...", "details": {} } }`.

| Service operation | Method and path | Notes |
|---|---|---|
| `login` / `logout` / `getCurrentSession` / `updateSession` | `POST /auth/login`, `POST /auth/logout`, `GET /auth/session`, `PATCH /auth/session` | `updateSession` only writes `name`/`avatarUrl`; role/org/identity fields are ignored server-side. |
| `changePassword` | `POST /auth/change-password` | Requires the current password. |
| Legal consent | `GET`, `POST /legal-consents/current` | Scoped to the authenticated identity. |
| Users | `GET /users?organisationId&role&email`, `GET/PUT/PATCH/DELETE /users/:id` | `PUT` is an admin/superadmin upsert; `PATCH` (self only) writes `avatarUrl`. |
| Patients | `GET /patients?organisationId&doctorId`, `GET/PUT/PATCH /patients/:id` | `PUT` is admin/doctor/superadmin only; self `PATCH` writes `name`/`email`/`phone`. |
| Doctors | `GET /doctors?organisationId`, `GET/PUT/PATCH /doctors/:id` | `PUT` is admin/superadmin only; self `PATCH` writes `name`/`email`/`phone`/`speciality`. |
| Organisations | `GET /organisations`, `GET/PUT/PATCH/DELETE /organisations/:id` | `PUT` (full upsert) is superadmin only; `PATCH` also allows an org's own admin. |
| ECG | `GET /ecg-records?organisationId&patientId&doctorId`, `GET /ecg-records/:id`, `POST /ecg-records/upload` (multipart), `PATCH /ecg-records/:id` (metadata only) | Files are never included in list responses. |
| Clinical reports | `GET /reports?organisationId&patientId&doctorId`, `GET/PUT /reports/:id` | `PUT` is an idempotent upsert so screens that mint client-side IDs keep working. |
| Pipeline report | `GET /reports/:id/pipeline` | Signal-processing view of a report. SAECG/QT fields the pipeline doesn't compute yet come back `null`, not fabricated numbers -- render "not yet available". |
| Audit logs | `GET /audit-logs?organisationId&actorRole`, `POST /audit-logs` | Actor/org/IP/timestamp are derived server-side. |
| Usage | `GET /usage?organisationId&doctorId`, `POST /usage` | Credits are calculated server-side. |
| Data reset | `POST /admin/application-data` | Privileged (superadmin) development operation. |

## Security requirements enforced by the backend, not the frontend

- The actor is always the server session, never an `organisationId`, role, or
  IP the browser supplies.
- Every fetch (not just list queries) is authorized server-side.
- List endpoints are paginated; ECG file data is never sent in a list response.
