# ECG Ingestion Flow After the P0 Fix

## Request path

```text
Doctor/Admin browser
  → POST /api/ecg-records/ingest (multipart)
  → authenticate and authorize patient scope
  → read and stage files under UUID upload session
  → compute request fingerprint
  → derive tenant/requester-scoped idempotency key
  → existing active/successful key?
       yes → return existing job
       failed → restage and requeue same job identity
       no → create ECGIngestJob(QUEUED)
  → HTTP 202 + igj-* + status URL
```

The request waits only for upload transfer, staging, fingerprinting, and a small database transaction. Parsing, canonicalization, durable object writes, and preprocessing occur after the response.

## Background path

```text
run_ingest_job(job_id)
  → own database session
  → conditional QUEUED check
  → RUNNING / LOAD_STAGED_UPLOAD
  → reopen UploadSession by validated UUID
  → verify patient still belongs to job organisation
  → INGEST_CANONICAL_RECORD
       → detect format
       → parser
       → metadata extraction
       → validation
       → canonical ECG model
       → initial artifacts
  → PREPROCESS
       → unchanged preprocessing implementation
       → preprocessed.npz
       → preprocessing_report.json
  → VERIFY_DURABLE_ARTIFACTS
       → verify explicit mandatory list
       → object-store read-back where required
       → SHA-256 each artifact
       → write and verify artifact_manifest.json
  → COMMIT_RECORD
       → insert ECGRecord with artifact manifest
       → set job SUCCEEDED and ecgRecordId
  → remove temporary upload session
```

## Failure path

```text
Any exception
  → rollback database transaction
  → remove partial local and durable canonical tree
  → persist job FAILED
       errorCode
       diagnostic errorMessage (operator record)
       safe API message
       completedAt
  → clean staging directory
```

## Idempotency

```text
fingerprint = SHA256(
  patient_id
  + sorted file names
  + SHA256(each file body)
)

effective_key = SHA256(
  organisation_id
  + requester_user_id
  + supplied Idempotency-Key OR fingerprint
)
```

The unique database constraint closes races. Multipart ordering does not change the fingerprint. The same successful upload cannot create another canonical ECG through the same operation. An explicit key reused with different bytes is rejected with 409.

## Frontend state

```text
Uploading... n%
  → 202 received
  → Processing ECG...
  → poll ingest job
       SUCCEEDED → fetch canonical ECG → existing audit/report navigation
       FAILED → show meaningful error → Retry Processing
```

## Operational limitation

The repository's existing FastAPI background-task mechanism is reused. State is durable, but task execution itself is process-local. A restart is detected as stale failure and is recoverable through retry; it is not automatically resumed by another instance.

