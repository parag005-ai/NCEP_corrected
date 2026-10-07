# NCEP End-to-End Defect Register

## BUG-E2E-001 — Ingest returns 504 after committing the ECG

- **Severity:** P0
- **Status:** Reproduced
- **Component:** Doctor upload / Netlify proxy / canonical ingest
- **Record:** `ecg-ed314afc`

### Steps

1. Log in as the doctor.
2. Open the ECG upload page and select `pat-001`.
3. Add `s0017lre.hea`, `s0017lre.dat`, and `s0017lre.xyz` together.
4. Start upload and wait.

### Actual

The progress indicator reaches 100%, then the UI displays `NCEP API request failed (504)`. The record later appears through the API with a canonical ID and derived ingestion metadata.

### Expected

The UI receives a stable job/record identity and an unambiguous terminal outcome. A timeout must not coexist with a committed but undisclosed record.

### Root cause

The canonical ingest performs the full ingestion pipeline synchronously behind the Netlify proxy. Processing exceeds the proxy response window.

### Fix

Return 202 quickly with an idempotent ingest job, execute processing asynchronously, expose status, and make retries idempotent. Alternatively guarantee bounded processing below the proxy timeout, though an asynchronous design is safer for medical files.

## BUG-E2E-002 — Canonical database record outlives its waveform artifact

- **Severity:** P0
- **Status:** Reproduced
- **Component:** Artifact storage / waveform API

### Actual

The canonical record reports 15 leads, 1000 Hz, 115200 samples, quality information, and beat count, but the waveform endpoint returns 404: `No waveform file for this record`.

### Expected

A committed canonical ECG guarantees retrievable waveform artifacts, or the record is atomically marked failed/unavailable with an actionable reason.

### Root cause

The active storage design relies on a local filesystem path while object backup is best effort. The waveform route reads the local path directly rather than the artifact repository/hydration abstraction. Ephemeral storage can therefore separate the database row from the data.

### Fix

Use durable object storage as the source of truth, store a required artifact manifest and checksums, verify mandatory uploads before success, and make every reader use the same repository. Do not swallow mandatory backup errors.

## BUG-E2E-003 — Report job stalls indefinitely at LOAD_GENERATION_CONTEXT

- **Severity:** P0
- **Status:** Reproduced
- **Job:** `rgj-1294b55f04b4`

### Actual

The job advances to `RUNNING` but remains at 0%, `LOAD_GENERATION_CONTEXT`, attempt 1, with no error and no report ID. No generated report exists.

### Expected

The stage completes or fails within a bounded interval, persists an error code/message, and transitions the job to a terminal state.

### Likely root cause

Context loading calls the ECG artifact repository and hydration before SP. The current record's local waveform is demonstrably absent, making hydration/object-backup retrieval the likely blocking boundary. Production stack details were not exposed, so the precise internal wait is not claimed as proven.

### Fix

Add hard timeouts and cancellation around list/download/hydration, validate the artifact manifest before job start, propagate exceptions, persist stage diagnostics, and enforce a watchdog that marks stale jobs `FAILED`.

## BUG-E2E-004 — Viewer is not connected to durable canonical waveform data

- **Severity:** P1
- **Status:** Confirmed by live API plus static trace
- **Component:** ECG viewer

### Actual

The canonical waveform API fails for the tested record, and the frontend viewer does not make a production call to that endpoint.

### Expected

The viewer requests authorized, downsampled canonical data and shows real leads with loading/error states and provenance.

### Fix

First repair artifact durability and repository-based waveform access. Then connect the viewer to the canonical waveform API, test lead selection/downsampling, and remove placeholder/mock paths.

## BUG-E2E-005 — UI advertises formats unsupported by canonical ingestion

- **Severity:** P2
- **Status:** Confirmed by static trace
- **Component:** Upload UI / parser registry

### Actual

The UI accepts or advertises EDF, PDF, PNG, and JPG, but the canonical detector/parser registry provides WFDB, CSV, XML, DICOM, and SCP-ECG only.

### Expected

Accepted extensions and user-facing format claims are generated from the backend capability contract or are otherwise kept exactly aligned.

### Fix

Remove unsupported formats from the UI or implement and test canonical parsers. Add a contract test comparing frontend accepted extensions to backend registered formats.

## BUG-E2E-006 — Ingestion and report preprocessing can diverge

- **Severity:** P2
- **Status:** Confirmed by static trace
- **Component:** Preprocessing / report signal processing

### Actual

Ingestion persists preprocessing-derived quality/beat metadata, while report generation reloads the raw bundle and preprocesses/analyzes it independently.

### Risk

The same ECG can expose one quality/beat result on the record and another in a report if versions, parameters, lead selection, or libraries differ.

### Fix

Adopt a single versioned computation contract. Either consume immutable preprocessing artifacts or explicitly recompute and record complete algorithm version, parameters, input checksums, and reconciliation rules.

## BUG-E2E-007 — No governed clinical interpretation layer

- **Severity:** P1 for clinical release
- **Status:** Not implemented / clinically unconfirmed
- **Component:** Clinical scoring and interpretation

### Actual

Technical measurements may be mapped, but no governed diagnostic scoring/classification/interpretation implementation and validation evidence was found. The current job produced no report in any case.

### Expected

Any clinical claim has a specified formula/threshold, version, provenance, uncertainty handling, validation evidence, and qualified clinical approval.

### Fix

Keep outputs explicitly technical until a clinical governance program supplies validated algorithms, representative datasets, target performance, regression controls, contraindications/limitations, and formal review.

## Remediation order

1. Repair ingest lifecycle/idempotency and artifact durability together.
2. Add bounded report-job failure semantics and observability.
3. Re-run the supplied WFDB bundle and verify real SP outputs through PDF retrieval.
4. Connect and validate the viewer.
5. Align advertised formats with implemented parsers.
6. Unify/version preprocessing provenance.
7. Complete separate clinical validation before diagnostic use.

