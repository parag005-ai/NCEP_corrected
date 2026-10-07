# NCEP P0 Remediation Report

## Status

The three audited P0 defects have been repaired in source code. Local ingestion, storage, idempotency, checksum, and stale-job tests pass. Production acceptance remains pending because the change has not been deployed, the PostgreSQL migration has not run in production, and the same real WFDB bundle has not yet been exercised against the repaired deployment.

No signal-processing algorithm, clinical threshold, score, or interpretation was changed.

## 1. What changed

### Asynchronous ingestion

`POST /api/ecg-records/ingest` now stages the multipart upload, persists an `ECGIngestJob`, and returns HTTP 202 with a stable `igj-*` operation identity. FastAPI background execution reopens the staged upload using a separate database session and persists stage, attempt count, canonical ECG ID, timestamps, error code, and terminal `SUCCEEDED` or `FAILED` state.

`GET /api/ecg-records/ingest-jobs/{job_id}` exposes authorized status polling. A stale queued/running operation is changed to terminal `FAILED` instead of remaining indeterminate.

### Idempotency

The service computes a SHA-256 request fingerprint from patient identity, normalized file names, and each file's SHA-256 digest. The effective key is tenant- and requester-scoped and may also incorporate an explicit `Idempotency-Key` header.

The database enforces one row per effective key. A retry of a successful or active operation returns the existing job. A failed operation can be restaged and retried under the same job identity. Reusing an explicit key for different bytes returns 409.

### Durable canonical artifacts

Canonical success now requires a defined artifact set:

- all original uploaded companion files;
- `waveform.npz`, `waveform.csv`, and waveform descriptor;
- all seven canonical metadata documents;
- processing manifest;
- preprocessed signal and preprocessing report;
- a final checksum-bearing artifact manifest.

Every mandatory artifact records its relative path, size, SHA-256 checksum, mandatory flag, and durable reference. In production `auto` storage mode resolves to Cloudinary. A missing configuration, failed upload, failed read-back, or checksum mismatch fails ingestion. Mandatory object-storage errors are no longer swallowed.

Filesystem mode remains available for tests and explicitly configured persistent volumes. Process-local storage is no longer the production default.

### Common artifact access

`ECGArtifactRepository` now materializes deterministic artifact paths through `FilesystemArtifactStore`, verifies the persisted manifest, and fails clearly when mandatory data is missing or altered. It no longer depends on an unbounded prefix listing to recover the report bundle.

The waveform and canonical download endpoints retain existing authorization checks but now resolve canonical data through the repository. A legacy record without canonical artifacts returns a clear 409 state. A new authorized artifact-manifest endpoint exposes integrity metadata without storage locations.

### Report failure semantics

Artifact loading and report-time signal-processing context preparation are bounded by configured timeouts. Exceptions return to `WorkflowOrchestrator`, which persists error code, error message, failed stage, completion timestamp, stage history, and terminal `FAILED` state.

An outer worker guard records `REPORT_WORKER_EXCEPTION` if an exception escapes normal stage handling. Polling/listing detects abandoned `RUNNING` jobs and records `REPORT_JOB_STALE` after the configured stale interval.

## 2. Why it changed

The prior request owned parsing, storage, preprocessing, and database commit. Netlify could time out while the backend continued and committed a record. The stored database row then referenced an ephemeral local file. Report generation entered context loading and could wait inside artifact recovery without returning control to the state machine.

The repair separates the request lifecycle from processing, makes canonical success conditional on durable verified artifacts, and guarantees bounded/terminal report state transitions.

## 3. API changes

### `POST /api/ecg-records/ingest`

- Previous: synchronous HTTP 201 with `ECGRecord`.
- New: HTTP 202 with `ECGIngestJobOut`.
- Optional request header: `Idempotency-Key`.
- Response includes job ID, status, current stage, attempt count, canonical ECG ID when successful, safe error information, timestamps, and status URL.

### `GET /api/ecg-records/ingest-jobs/{job_id}`

Returns the current authorized ingestion operation. Cross-organisation callers receive 404, preserving tenant non-disclosure.

### `GET /api/ecg-records/{id}/waveform`

Uses the canonical artifact repository and retains lead selection/downsampling. Missing, unverifiable, or unhydratable canonical data returns 409 instead of reading a process-local path directly.

### `GET /api/ecg-records/{id}/artifact-manifest`

Returns sanitized manifest fields: record ID, storage mode, verification time, relative paths, sizes, checksums, and mandatory flags. It does not expose private Cloudinary IDs or local paths.

## 4. Database changes

Migration `9f42a81ce310` adds:

- `ecg_records.artifact_manifest` JSON, nullable for compatibility with existing records;
- `ecg_ingest_jobs` with lineage, unique idempotency key, request fingerprint, staged upload ID, file names, request metadata, status/stage, attempts, canonical ECG ID, errors, and timestamps;
- indexes for idempotency, fingerprint, patient, organisation, requester, status, and resulting ECG ID.

The migration is additive and does not delete or rewrite existing ECGs. Existing rows without a canonical record ID or retrievable artifacts return an explicit unavailable response.

## 5. Storage changes

Production `auto` mode now selects Cloudinary as the durable source. Local files are staging/cache. Each canonical write requires the corresponding private raw object write. Finalization downloads/verifies required durable objects, computes SHA-256 values, writes the final artifact manifest, and verifies that manifest.

If production uses a genuinely persistent mounted filesystem instead, deployment must explicitly configure `ECG_DURABLE_STORAGE_MODE=filesystem`. Cloudinary mode requires the existing Cloudinary credentials.

## 6. Job lifecycle

```text
POST ingest
  → stage upload
  → persist QUEUED job
  → 202 + igj ID
  → background runner
  → RUNNING / LOAD_STAGED_UPLOAD
  → INGEST_CANONICAL_RECORD
  → PREPROCESS
  → VERIFY_DURABLE_ARTIFACTS
  → COMMIT_RECORD
  → SUCCEEDED + ecgRecordId

Any exception
  → rollback database work
  → remove partial canonical artifacts
  → FAILED + errorCode + safe client message + completedAt
```

## 7. Idempotency mechanism

The fallback fingerprint is deterministic across multipart file order. Tenant and requester scope prevent one organisation from discovering or reusing another's operation. The database unique constraint closes concurrent duplicate races. Retrying a failed job updates the same operation with a new staging ID; it cannot create a second successful canonical record under that operation.

## 8. Artifact manifest

The manifest schema is version `1.0`. Each mandatory artifact includes:

- `relativePath`;
- `sizeBytes`;
- `checksumSha256`;
- `mandatory=true`;
- internal `durableReference`.

The database stores the manifest for quick integrity/provenance access. The manifest is also stored as `manifest/artifact_manifest.json`. API output removes the internal durable reference.

## 9. Failure semantics

- Upload parsing/validation problems become terminal failed ingest jobs.
- Durable storage failure prevents `ECGRecord` creation.
- Missing/corrupt canonical artifacts raise `ECGArtifactUnavailableError`.
- Context artifact loading and report-time context SP preparation use bounded waits.
- Escaped report worker exceptions become terminal `FAILED`.
- A stale `RUNNING` report becomes `FAILED` with `REPORT_JOB_STALE`.
- Failures do not become empty successful reports.

## 10. Frontend behavior

Doctor and admin upload pages retain the existing design. The service now:

1. uploads the multipart body;
2. receives the 202 ingest job;
3. switches the UI to `Processing ECG...`;
4. polls the job endpoint;
5. loads the canonical ECG only after `SUCCEEDED`;
6. shows the persisted meaningful failure and a `Retry Processing` action after `FAILED`.

The existing report navigation occurs only after a successful canonical record is returned.

## 11. Files modified

| File | Change | Reason | Risk |
|---|---|---|---|
| `backend/app/config.py` | Durable-mode and timeout settings | Enforce production durability and bounded report context | Deployment must provide durable storage credentials/configuration |
| `backend/app/models.py` | Added ingest-job model and ECG artifact manifest | Persist operation identity, state, errors, and integrity metadata | Requires migration before new API is used |
| `backend/app/schemas.py` | Added ingest-job response contract | Return pollable async state | Frontend/backend must deploy together |
| `backend/app/ingestion/idempotency.py` | Deterministic fingerprint and scoped key | Prevent duplicate canonical records | Same bytes/patient/requester intentionally resolve to one operation |
| `backend/app/ingestion/job_service.py` | Background ingestion lifecycle, mandatory artifact definition, terminal persistence | Remove long processing from request and gate success | In-process background tasks are not a distributed queue; restart recovery relies on stale failure/retry |
| `backend/app/ingestion/upload_orchestrator.py` | Reopen UUID-scoped staged uploads | Allow post-response processing | Staging remains local until worker begins; a restart causes explicit failure/retry |
| `backend/app/storage/cloudinary_backup.py` | Required upload mode and bounded download timeout | Stop swallowing mandatory durable-write failures | Production ingest fails until Cloudinary is correctly configured |
| `backend/app/storage/file/filesystem.py` | Materialization, manifest finalization, checksum/read-back verification | Make local disk cache/staging rather than silent source of truth | Additional object-store I/O increases background processing time |
| `backend/app/reporting/repositories/ecg_artifact_repository.py` | Manifest verification and deterministic per-artifact materialization | Shared durable access for reports/waveform | Corrupt legacy data now fails explicitly |
| `backend/app/reporting/context/loader.py` | Bounded artifact/SP context preparation | Return control so orchestrator can fail | Timeout values require production tuning |
| `backend/app/reporting/api/service.py` | Outer worker exception-to-FAILED guard | Prevent escaped exceptions stranding jobs | Unexpected worker errors now expose terminal failure rather than indefinite retry |
| `backend/app/reporting/repositories/job_repository.py` | Stale RUNNING detection | Watchdog-compatible terminal behavior | Long stages must finish/heartbeat inside configured interval |
| `backend/app/reporting/api/schemas.py` | Exposes the persisted failed stage in the status response | Let clients distinguish the terminal failure boundary | Frontend contract must remain aligned |
| `backend/app/reporting/api/routes.py` | Applies stale check and safe messages | Polling repairs abandoned state safely | GET/list performs a narrow state mutation for stale jobs |
| `backend/app/routers/ecg.py` | Async ingest/status endpoints, retry, repository waveform/download, manifest endpoint | Repair all three P0 boundaries | API contract changes from ECG record to job response |
| `backend/alembic/versions/9f42a81ce310_add_async_ingest_jobs_and_artifact_manifest.py` | Additive schema migration | Persist new lifecycle and manifest | Must be applied before deployment |
| `NCEPfrontend/src/services/contracts.ts` | Ingest-job runtime schema | Validate new 202/status payloads | Must match backend enum/fields |
| `NCEPfrontend/src/services/ecg.service.ts` | Upload, accept, poll, fail/succeed, then fetch ECG | Correct frontend semantics | Poll interval adds status traffic while processing |
| `NCEPfrontend/src/app/doctor/ecg-upload/page.tsx` | Processing stage callback and retry label | Avoid false upload-failed message | Minimal UI-only change |
| `NCEPfrontend/src/app/admin/ecg-upload/page.tsx` | Same async state handling as doctor | Keep role flows consistent | Minimal UI-only change |
| `backend/tests/test_p0_remediation.py` | Idempotency, staging, manifest, storage failure, stale report tests | Regression coverage | None in runtime |

## 12. Test results

Executed locally:

- Python compilation: passed.
- Ingestion/storage/parser regression set: 15 passed.
- New P0 tests: 6 passed.
- Combined result: 21 passed, 0 failed, 2 pre-existing pydicom deprecation warnings.
- Alembic head discovery: `9f42a81ce310` is the single head.

Unable to execute on this Windows host:

- reporting/API suite: Windows Application Control blocked a downloaded scikit-learn DLL during NeuroKit import;
- frontend TypeScript compiler: dependency installation could not complete inside the managed environment after package-store access/download failures;
- full SQLite migration chain: pre-existing PostgreSQL-specific migration `d4def27b9fa6` uses `ALTER ... TYPE ... ::timestamptz`, which SQLite cannot execute.

These are recorded as blocked, not passed.

## 13. Acceptance checklist

- [x] Source implementation no longer waits for parsing/preprocessing before returning 202.
- [x] Stable ingest operation identity is persisted.
- [x] Idempotency fingerprint and database uniqueness are implemented and unit-tested.
- [x] Canonical success is gated by mandatory durable artifacts and checksums.
- [x] Waveform code uses the artifact repository rather than a raw local path.
- [x] Missing/corrupt artifacts produce explicit failure paths.
- [x] Report artifact/context loading is bounded.
- [x] Worker exceptions and stale jobs have terminal failure semantics.
- [x] No SP or clinical algorithms were modified.
- [ ] Migration applied to production PostgreSQL.
- [ ] Cloudinary/persistent-volume configuration verified in production.
- [ ] Repaired backend/frontend deployed.
- [ ] Same real WFDB upload returns 202 and reaches ingest `SUCCEEDED`.
- [ ] Retry/duplicate production requests return the same successful operation/ECG.
- [ ] Production waveform retrieval succeeds after instance restart/cache loss.
- [ ] Production report context completes and real SP outputs appear.
- [ ] Summary, detailed, HTML, PDF, and PDF retrieval pass.

## 14. Remaining blockers

The remediation must not be declared fully accepted until deployment and the real post-fix WFDB chain pass. The in-process FastAPI background runner is intentionally reused because the repository has no broker/worker infrastructure. It solves the proxy timeout and persists state, but a process restart before/during execution results in stale failure and user retry rather than automatic cross-process resumption. A durable external queue can be considered later as an operational hardening change, not as part of this scoped repair.

