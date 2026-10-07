# NCEP / CardioNexus End-to-End Functional Validation

**Execution date:** 2026-10-06  
**Environment:** Production demo frontend (`ncep-frontend.netlify.app`) and configured Render backend  
**Test record:** `s0017lre` WFDB bundle (`.hea`, `.dat`, `.xyz`)  
**Selected patient:** Anaya Rao (`pat-001`)  
**Created ECG:** `ecg-ed314afc`  
**Canonical record ID:** `ae4d60a2-9c5d-4783-a82a-1da59b922d65`  
**Report job:** `rgj-1294b55f04b4`

## 1. Executive conclusion

The complete clinical workflow is **not operational end to end**. Authentication, role boundaries, WFDB detection, parsing, canonical record construction, validation, and ingestion-time preprocessing work. The doctor cannot, however, upload the supplied recording and receive a generated report with genuine report-time derived measurements.

The first user-visible production break is the canonical ingest request: the upload reaches 100%, then the Netlify-facing request returns HTTP 504. The backend nevertheless completes enough work to commit `ecg-ed314afc`, leaving the UI unaware of a successfully created record. The next hard data-path break is artifact durability/retrieval: the waveform endpoint returns `No waveform file for this record`. A report job can be created, but it remains indefinitely at `RUNNING`, 0%, `LOAD_GENERATION_CONTEXT`, so report-time signal processing, report assembly, HTML/PDF generation, and artifact retrieval never occur.

**Answer to the acceptance question:** No—the doctor cannot presently upload the supplied WFDB bundle and receive a completed report containing genuine derived measurements.

## 2. Scope and method

The validation combined:

- browser execution of the doctor login and upload journey;
- live API checks using the supplied doctor, admin, and superadmin demo accounts;
- negative authorization and malformed-upload tests;
- inspection of the exact production records and report-job state;
- code-level tracing from UI request through ingestion, storage, preprocessing, signal processing, report construction, and retrieval.

The supplied medical files were transmitted only after the user's explicit authorization. No source code was changed.

## 3. Test data integrity

The header identifies a 15-signal, 1000 Hz, 115200-sample recording. The `.dat` file supplies the 12 standard leads and `.xyz` supplies vectorcardiographic X/Y/Z channels. The live canonical record preserved:

- source format: `WFDB`;
- sampling rate: `1000.0 Hz`;
- duration: `115.2 s`;
- sample count: `115200`;
- lead count: `15`;
- leads: I, II, III, aVR, aVL, aVF, V1–V6, X, Y, Z;
- units: `mV`;
- XYZ available: `true`.

This demonstrates that the format detector, WFDB parser, companion-file resolution, canonical builder, and database persistence executed successfully.

## 4. Authentication

All three supplied accounts authenticated successfully and returned the expected roles:

- Doctor: `user-doctor-001`, role `doctor`;
- Admin: `user-admin-001`, role `admin`;
- Superadmin: `user-superadmin-001`, role `superadmin`.

The doctor browser session reached the doctor dashboard. Status: **VERIFIED_WORKING**.

## 5. Authorization and tenant boundaries

Unauthenticated record access returned 401. A doctor request for known record `ecg-005` outside the doctor's visible scope returned 404, while admin and superadmin requests returned 200. This is a useful non-disclosing tenant boundary. Status: **VERIFIED_WORKING** for the tested cases.

## 6. Doctor upload UI

The UI accepted the three files together, displayed each filename and a combined size of 3.30 MB, and allowed association with `pat-001`. Upload progress reached 100%. It then showed `NCEP API request failed (504)`.

Status: **BROKEN (P0)** for completion semantics. The progress bar reflects request-body transfer, not successful ingestion. Because the backend committed the record after the proxy timed out, retrying can create duplicates or orphaned records from the user's perspective.

## 7. API routing and availability

Both the Netlify-proxied health endpoint and direct Render health endpoint returned 200. The backend was therefore available; the 504 was specific to the long synchronous ingest path. `netlify.toml` proxies `/api/*` to the Render backend.

Status: health **VERIFIED_WORKING**; long-operation architecture **BROKEN (P0)**.

## 8. Upload endpoint selection

The active frontend uses the canonical `POST /api/ecg-records/ingest` path rather than the legacy upload route. This is the correct architectural choice. The canonical route performs format detection, parsing, metadata extraction, validation, model construction, artifact storage, preprocessing, and persistence synchronously before responding.

Status: endpoint wiring **VERIFIED_WORKING**, response-time contract **BROKEN**.

## 9. Format detection

The supplied three-file bundle was correctly detected as WFDB. An orphan `.dat` upload was correctly rejected with 422 and an actionable requirement for a matching `.hea` file. A request missing both files and patient ID also returned 422.

Status: **VERIFIED_WORKING** for tested WFDB and negative cases.

## 10. Parsing

The WFDB parser followed the header references and loaded all 15 channels from `.dat` and `.xyz`. Signal dimensions in the live record match the header exactly. Status: **VERIFIED_WORKING**.

CSV, XML, DICOM, and SCP-ECG parsers are registered in code but were not live-tested because no fixtures for those formats were supplied. They are classified **PARTIALLY_WORKING / not live validated**, not certified.

EDF, PDF, PNG, and JPG appear in UI acceptance/advertising, but no equivalent canonical parsers are registered. Status: **NOT_IMPLEMENTED / contract mismatch (P2)**.

## 11. Metadata extraction

The source header contains age and sex, while the selected platform patient supplies the workflow association. The record was accepted with a structured warning that `patient_id`, `name`, `date_of_birth`, `hospital`, `clinician`, and `clinical_history` were missing from extracted source metadata.

Status: **PARTIALLY_WORKING (P2)**. The warning is appropriate, but source metadata, selected patient data, and provenance should be presented distinctly so that missing source fields are not confused with missing platform patient fields.

## 12. Validation

The record persisted with `validationStatus=WARNING`, and the validator name, missing-field list, and recommendation were retained. A technically usable waveform was not rejected merely because optional metadata was absent. Status: **VERIFIED_WORKING**.

## 13. Canonical ECG construction

The system created `ecg-ed314afc` with canonical record ID `ae4d60a2-9c5d-4783-a82a-1da59b922d65`. Sampling, duration, channels, units, validation result, quality metadata, and beat count were accessible through the record API. Status: **VERIFIED_WORKING**, with the important caveat that the UI received 504 and did not learn this identity.

## 14. Ingestion-time preprocessing

The record contains `qualityScore=0.120720245446648`, `qualityFlags=["low_snr"]`, and `beatCount=139`. These values demonstrate that ingestion-time preprocessing executed and results were persisted. Status: **VERIFIED_WORKING** for execution and persistence.

These values are technical outputs only. They are not independently clinically validated by this audit.

## 15. Artifact storage and durability

`GET /api/ecg-records/ecg-ed314afc/waveform?...` returned 404 with `No waveform file for this record`. The waveform route checks a stored local path directly. The filesystem storage layer writes locally and treats Cloudinary backup as best effort, while the report repository has a separate hydration path.

Status: **BROKEN (P0)**. A database record can outlive its waveform artifact, violating the canonical record's durability contract. Backup failure must not be silently compatible with a successful commit when the host filesystem is ephemeral.

## 16. ECG viewer

The current record cannot be viewed through the waveform API because its waveform file is absent. Static frontend tracing also found no production call from the viewer to the canonical waveform endpoint. Status: **BROKEN / NOT_CONNECTED (P1)**.

## 17. Report job creation

Creating a report-generation job succeeded. Job `rgj-1294b55f04b4` moved from `QUEUED` to `RUNNING`, with `attemptCount=1`. Status: job submission **VERIFIED_WORKING**.

## 18. Generation-context loading

The job remained at progress 0 and stage `LOAD_GENERATION_CONTEXT`, without a report ID, error code, error message, or terminal failure state. The report context loader hydrates and loads the ECG artifact bundle before report-time signal processing.

Status: **BROKEN (P0)**. The verified missing waveform plus the stage location makes artifact hydration/retrieval the strongest causal explanation. This is an evidence-based inference; the production worker's internal exception/stack trace was not exposed.

## 19. Signal-processing execution

The report-time signal-processing adapter was never reached for this record. Consequently, heart rate, RR, QRS, QT, QTc, Tpeak–Tend, P-wave metrics, signal-averaged metrics, quality outputs, and report-specific R-peak outputs were not produced in the tested journey.

Status: **NOT_CONNECTED in the live journey**, blocked upstream at context loading. Static code shows an SP builder connected after context loading; that does not qualify as live verification.

## 20. Signal-processing provenance

The report path reloads the canonical raw waveform and invokes preprocessing/analysis again instead of consuming the preprocessing artifact created during ingestion. This creates two computation paths whose versions and outputs may diverge.

Status: **PARTIALLY_WORKING (P2)** by design trace. Reports should record algorithm version, parameters, input artifact checksum, lead selection, sampling rate, warnings, and output provenance.

## 21. SP-to-report field mapping

Static mapping exists for technical measurements such as heart rate, RR, QRS, QT, Bazett/Fridericia QTc, Tpeak–Tend, P-wave duration/dispersion, RMS/LAS metrics, filtered durations, R-peak count, and quality flags. None was persisted or rendered for the current job because SP never executed.

Status: mapping **PARTIALLY_WORKING by code trace**; production result **NOT_CONNECTED**. The detailed field matrix is in `NCEP_E2E_SP_REPORT_TRACE.csv`.

## 22. Summary report

No report record was created for `ecg-ed314afc`; querying generated reports returned an empty list. Status: **NOT_CONNECTED (P0 upstream blocker)**.

## 23. Detailed report

No detailed report was created. Status: **NOT_CONNECTED (P0 upstream blocker)**.

## 24. HTML rendering

The pipeline did not reach HTML rendering. No claim can be made about production rendering correctness for this record. Status: **NOT_CONNECTED**.

## 25. PDF rendering

The pipeline did not reach PDF rendering. No PDF exists for this job. Status: **NOT_CONNECTED**.

## 26. Report artifact storage and retrieval

There is no report ID and no report artifact for the current job. Authorization of a real artifact download could therefore not be tested. Status: **NOT_CONNECTED** due to the upstream context-load failure.

## 27. Clinical validity

The system does not currently provide a governed, clinically validated scoring/classification/interpretation layer for the requested diagnostic conclusions. The source header's clinical comments are historical input metadata, not a platform-derived diagnosis. All clinical findings must remain **CLINICALLY_UNCONFIRMED**.

Technical restoration of the pipeline is insufficient for clinical release. Clinical readiness additionally requires specified formulas and thresholds, algorithm/version governance, traceable inputs, validation datasets, performance targets, edge-case handling, reproducibility tests, and qualified clinical review.

## Severity summary

| Severity | Finding | Consequence |
|---|---|---|
| P0 | Synchronous ingest returns 504 but commits a record | Doctor sees failure; retry/orphan risk |
| P0 | Canonical waveform is not durably retrievable | Viewer and report context cannot use the ECG |
| P0 | Report job stalls at context load without terminal failure | No measurements or report; misleading RUNNING state |
| P1 | Viewer is not wired to canonical waveform data | No reliable live ECG visualization |
| P1 | Clinical interpretation/scoring is absent or unvalidated | Not suitable for diagnostic claims |
| P2 | UI advertises formats missing from canonical parser registry | Predictable upload failures |
| P2 | Ingestion and report preprocessing are separate paths | Provenance and reproducibility risk |

## First break and minimum fixes

The **first user-visible break** is the 504 on `POST /api/ecg-records/ingest`. The **first downstream data availability break** is the missing waveform artifact, which prevents context loading.

Minimum fixes to restore upload-to-technical-report behavior:

1. Make ingest asynchronous (or otherwise return within the proxy limit) with an idempotency key and a pollable terminal state. Never leave the client with failure after committing an undiscoverable record.
2. Make canonical artifacts durable and transactional: use persistent/object storage as the source of truth, verify backup before committing success, make all readers use the same artifact repository/hydration abstraction, and impose bounded timeouts with terminal job failure.

To restore the complete workflow including visualization, a third fix is required: connect the viewer to the canonical waveform API and make that endpoint hydrate/read durable storage rather than a process-local path.

## Final disposition

**Release disposition: FAIL for complete end-to-end workflow.** The platform demonstrates a sound ingestion skeleton and correctly parses the supplied waveform, but the production request lifecycle and artifact durability boundary prevent the ECG from reaching report-time signal processing and output generation.

