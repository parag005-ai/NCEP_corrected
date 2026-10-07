# NCEP code-level functional audit

Audit date: 2026-10-06  
Scope: the repository at `ncep-main`, inspected read-only. No production source was modified.

## Scope and evidence standard

This audit traces source-level execution paths. A feature is `VERIFIED_WORKING` only when a route/UI entry point reaches the implementation through a real call chain. A module or function that exists but is not invoked is not counted as integrated. `CLINICALLY_UNCONFIRMED` means the implementation or numerical output exists, but this repository does not contain a medical approval/validation source for its clinical use.

The attached `NCEP_FULL_FUNCTIONAL_AUDIT.xlsx` was treated as background evidence from an earlier UI/runtime audit. Its findings were not used as proof of the current source state where source paths differ. In particular, the current source contains the canonical `/api/ecg-records/ingest` route and report-time SP adapter that the workbook's legacy upload findings do not trace.

No `NCEP_SP_INTEGRATION_DATA_CONTRACT.md`, separate implementation specification, requirements document, or clinical-rule approval document was found in the repository. The executable module READMEs, code docstrings, schemas, tests, and frontend contracts are therefore the available planned-functionality sources. This limits requirement certainty for policy and clinical claims.

The full row-per-functionality inventory is in `NCEP_CODE_FUNCTIONAL_AUDIT.csv`; exact gaps and execution steps are in `NCEP_CODE_GAPS.csv` and `NCEP_CODE_TRACE.csv`.

## Repository architecture map

```text
NCEPfrontend (Next.js)
  doctor/admin upload pages
      -> services/ecg.service.ts: ingestECGRecord
      -> POST /api/ecg-records/ingest

backend (FastAPI)
  routers/ecg.py: ingest_ecg
      -> UploadOrchestrator
      -> create_ecg_record
          -> format detector -> parser factory -> format parser
          -> metadata extraction -> validation -> ECGRecordBuilder
          -> StorageOrchestrator (canonical waveform/metadata/manifest)
      -> PreprocessingOrchestrator (separate preprocessing artifacts)
      -> ECGRecord database summary row

  report page -> POST /api/report-generation/jobs
      -> create_generation_job -> BackgroundTasks -> run_generation_job
      -> WorkflowOrchestrator
          -> GenerationContextLoader
              -> ECGArtifactRepository
              -> build_signal_processing_outputs
                  -> WaveformReader -> analyze_waveform
          -> visualization -> summary/detailed builders
          -> HTML renderer -> Chromium PDF -> artifact repository
```

Major packages and real responsibilities:

| Area | Entry / responsibility | Current connection |
|---|---|---|
| Frontend | `NCEPfrontend/src/app/doctor/ecg-upload/page.tsx` | Uses the canonical multi-file `ingestECGRecord` path. |
| Ingestion | `backend/app/routers/ecg.py:ingest_ecg` | Canonical, authenticated, artifact-producing ingest endpoint. |
| Legacy ingestion | `backend/app/routers/ecg.py:upload_ecg` | Public endpoint that only stores a row/raw file and is not report-ready. |
| Canonical model | `backend/app/ecg/models/*`, `ECGRecordBuilder` | Parser results converge through one validated builder. |
| Preprocessing | `backend/app/preprocessing/pipeline.py` | Runs during canonical ingest and writes an NPZ + JSON report. |
| Signal Processing | `backend/app/signal_processing/analysis.py` | Runs at report-context load, not during ingest. |
| Reporting | `backend/app/reporting/*` | Seven-stage workflow creates visual, HTML, PDF, and metadata artifacts. |
| Database | `backend/app/models.py`, reporting models/migrations | Stores summary lineage and report jobs/artifacts. SP results themselves are not persisted. |
| Authorization | `backend/app/security.py`, `reporting/access.py` | Applies roles and tenant/patient access in backend paths. |

## Planned versus implemented findings

### Ingestion and canonical ECG

The canonical path is implemented and connected:

```text
POST /api/ecg-records/ingest
  -> UploadOrchestrator.create_session
  -> create_ecg_record
  -> detect_format / get_parser / parser.parse
  -> MetadataOrchestrator.extract
  -> ValidationOrchestrator.validate
  -> ECGRecordBuilder.build
  -> StorageOrchestrator.store
  -> PreprocessingOrchestrator.run
  -> relational ECGRecord row
```

`backend/app/ingestion/record_creator.py:60-75` fixes that sequence, and `ValidationOrchestrator` raises before the builder when aggregate validation is `FAIL`. The detector and parser registry actively support WFDB, CSV, XML, DICOM, and SCP-ECG. It rejects empty/mixed/unknown uploads and WFDB companion files without a `.hea` header. Validation covers supported format, readable/non-empty source files, waveform sample consistency and finite data, canonical lead count, sampling rate/sample count/duration consistency, recording/patient metadata, and device-provided quality indicators.

Canonical storage is report-ready: raw sources, NPZ/CSV waveform, waveform descriptor, seven metadata documents, validation manifest, preprocessing artifacts and preprocessing JSON are written under one record directory. Failure rolls back the directory; the endpoint also removes artifacts if later preprocessing/database work fails.

The important ingestion gap is the still-exposed `POST /api/ecg-records/upload` path (`backend/app/routers/ecg.py:111-181`). It does not call `create_ecg_record`, does not validate/build/store canonical artifacts, and only best-effort parses a CSV's metadata. `ECGArtifactRepository.load_bundle` refuses such records because `record_id` is absent. This is a high-severity *route divergence*, not a claim that canonical ingestion itself is broken.

### Preprocessing and quality

`PreprocessingOrchestrator.run` applies filtering, baseline correction, normalization, beat detection and quality calculation to every canonical lead, preserving the canonical waveform rather than overwriting it. The ingestion score, beat count, and flags are persisted on `ECGRecord` and in the preprocessing report.

There is no documented clinical validation source for this ingestion quality score or a clinical acceptance cutoff, so its availability is `CLINICALLY_UNCONFIRMED`, not diagnostic.

The reporting path does **not** double-preprocess a signal. It loads the canonical raw waveform and lets `app/signal_processing/analysis.py` perform the biomedical pipeline's preprocessing. The ingestion preprocessed artifact is discoverable in `ECGArtifactRepository` but has no downstream consumer. That is a partially implemented ownership boundary: it is not evidence of double transformation, but it is unused persisted work and needs an explicit architecture decision.

### Signal Processing and NCEP → SP integration

The integration is live, not merely vendored. `GenerationContextLoader.load` calls `build_signal_processing_outputs`; it loads canonical waveform artifacts through `WaveformReader`, then calls `analyze_waveform`. The adapter normalizes lead naming and calls the P-wave, QRS/R-peak, T-wave, QT/QTc, P-SAECG, and QRS-SAECG modules. Its raw metrics are mapped into `GenerationContext.signal_processing`.

```text
ECGRecord.record_id
  -> ECGArtifactRepository.load_bundle
  -> WaveformReader.read_from_artifacts
  -> analyze_waveform(leads, sampling_rate_hz)
  -> SignalProcessingResult.metrics
  -> build_signal_processing_outputs
  -> GenerationContext.signal_processing
  -> section builders -> HTML/PDF/API summary
```

The adapter maps heart rate, QRS durations, QT/QTc, Tpeak–Tend, dispersion, P-wave measures, RMS/LAS values, beat-selection values, basic QC state, R-peak count and analyzed leads. `clinical_findings` and waveform annotations intentionally stay unavailable.

The repository lacks the requested named SP integration data-contract document. The actual contract is an in-code mapping only. No typed/persisted `SignalProcessingResult` entity or versioned per-value provenance/confidence model exists; a result is recomputed while building each report context. This makes SP output integration `PARTIALLY_WORKING` rather than broken.

### Clinical rules and signal quality

Raw computation should not be mistaken for a clinically approved classification. The SP README explicitly excludes a formal Signal Quality Score, normal/abnormal classification, scoring thresholds, clinical interpretation/narrative, and vector-magnitude SAECG methodology pending medical-team confirmation. The corresponding report sections remain the exact placeholder `Awaiting Signal Processing Results`.

QT/QTc algorithms, including Bazett and Fridericia metrics, exist in `qt_module.py` and flow into reports. They are raw technical results. The repository contains no clinical validation/approval source establishing product-level cutoffs, sex-specific thresholds, diagnostic flags, recommendations, or normal/abnormal use. These findings are therefore `CLINICALLY_UNCONFIRMED`; the audit does not assert that the formulas are clinically incorrect.

### Report generation and artifacts

The production pipeline is fully assembled in `backend/app/reporting/orchestrator/pipeline.py` in this order:

```text
LoadGenerationContextStage
  -> GenerateVisualizationsStage
  -> BuildSummaryReportStage
  -> BuildDetailedReportStage
  -> RenderHTMLDocumentsStage
  -> GeneratePDFDocumentsStage
  -> StoreReportArtifactsStage
```

`POST /api/report-generation/jobs` authorizes an ECG record, creates a job, and schedules `run_generation_job` via FastAPI background tasks. The orchestrator claims jobs, logs stage executions, retries declared transient failures, supports cancellation, records failure details, and invokes cleanup for failure/cancellation.

The context loader re-resolves all upstream identities from the ECG record, verifies job/record patient and organization lineage, re-applies access checks, and requires canonical artifacts. Summary and detailed builders use the same immutable context. HTML and PDF renderer stages precede artifact registration and the API exposes summary, HTML, PDF, and individual artifact retrieval.

Report field coverage is partial by design. Raw SP measurements flow into measurement sections. Rhythm classification, PR interval, frontal axes, waveform annotations, clinical flags/findings, interpretation, confidence, integrated assessment, and recommendations lack an approved producer and remain explicit placeholders. This is the exact downstream breakpoint for those fields—not a generic report failure.

### API, database, frontend, and authorization

The frontend upload page calls `ingestECGRecord`, then routes to the summary page. That page creates a report-generation job when no generated report exists and polls it to completion. Thus the canonical UI path reaches SP and report generation.

There are two overlapping report concepts: legacy `ClinicalReport` rows from `/api/reports` and versioned `GeneratedReport`/`ReportGenerationJob`/`ReportArtifact` rows. Upload creates the legacy row, while the report page generates a distinct report by ECG record ID. They share UI flow but have no explicit persistence relation, which weakens provenance and lifecycle clarity.

Backend authentication verifies signed JWTs and user existence, and route dependencies enforce role capability. ECG/report access applies patient identity and organization/shared-patient scope. The code is organization-scoped for doctors, not assignment-scoped. Whether assignment-scoped doctor access is required is not defined in this repository, so it is `REQUIREMENT_UNCLEAR`, not declared a defect.

Logout removes the cookie but does not revoke the stateless JWT. The backend README describes this exact model. Immediate revocation is therefore a product/security-policy question absent from the repository requirements.

The doctor ECG viewer is the clear frontend disconnect: it loads record metadata but does not call the implemented `/api/ecg-records/{id}/waveform` endpoint. It cannot claim to display the selected canonical waveform until that connection is made.

## Exact critical and high breakpoints

| ID | Status | Exact breakpoint | Impact |
|---|---|---|---|
| ING-008 / REP-008 | PARTIALLY_WORKING | `routers/ecg.py:upload_ecg` bypasses `create_ecg_record`; `ECGArtifactRepository.load_bundle` rejects its missing `record_id`. | A successful legacy upload is not report-ready. |
| SP-003 | PARTIALLY_WORKING | `signal_processing_builder.py` maps values directly to context with no named versioned external contract or persisted SP result. | Weak compatibility, provenance, and reproducibility. |
| SP-004 | NOT_IMPLEMENTED | SP README explicitly states scoring has no formula; builder exports no score. | No formal SP quality score/acceptance decision. |
| SP-005 / CLN-002 | CLINICALLY_UNCONFIRMED | `build_signal_processing_outputs` deliberately sets `clinical_findings` to awaiting; section builders retain placeholders. | No clinical classification, narrative, or recommendation. |
| REP-007 | PARTIALLY_WORKING | No upstream producer/mapping for rhythm, PR, axes, annotations, clinical flags/findings, confidence, or recommendations. | Those report fields remain placeholders. |
| UI-003 | NOT_CONNECTED | `DoctorECGViewer` does not request `/waveform`. | Viewer is not showing selected canonical waveform. |
| CLN-001 | CLINICALLY_UNCONFIRMED | Raw QT/QTc and SAECG metrics lack repository clinical-validation evidence. | Numerical output must not be treated as approved diagnostic output. |

## End-to-end transition assessment

| Transition | Status | Evidence |
|---|---|---|
| ECG input → authenticated multi-file ingest | VERIFIED_WORKING | `doctor/ecg-upload/page.tsx` → `ingestECGRecord` → `ingest_ecg` |
| Ingest → canonical ECG + validation | VERIFIED_WORKING | `create_ecg_record` fixed sequence |
| Canonical ECG → preprocessing artifact | VERIFIED_WORKING | `PreprocessingOrchestrator.run` in `ingest_ecg` |
| Canonical ECG → SP execution | VERIFIED_WORKING | Context loader → SP adapter at report generation |
| SP result → report context | VERIFIED_WORKING for mapped raw metrics | `build_signal_processing_outputs` returns available context sections |
| Context → summary/detailed report | VERIFIED_WORKING | builders are active pipeline stages |
| HTML → PDF → artifact retrieval | VERIFIED_WORKING | render/PDF/store stages and API routes |
| Clinical result → clinical interpretation/recommendations | CLINICALLY_UNCONFIRMED | explicit placeholders pending governed rules |

The first blocker for the **canonical** end-to-end workflow is not a code-path break: it is clinical readiness. Raw reports can be generated; approved diagnostic interpretation cannot. The first code-path blocker applies only to the legacy `/upload` route, which creates a noncanonical record.

## Implementation order based on evidence

### Phase 1 — Must fix before integration

1. Eliminate or clearly fence the legacy `/upload` endpoint so every user-visible ECG upload produces canonical artifacts.
2. Align the frontend accepted extensions with the parser registry.
3. Connect the ECG viewer to the waveform endpoint.

### Phase 2 — Required for SP integration

1. Publish `NCEP_SP_INTEGRATION_DATA_CONTRACT.md` with field names, types, units, null behavior, input identity, lead mapping, preprocessing boundary, output provenance and contract version.
2. Decide whether stored NCEP preprocessing is input to SP or an ingestion-only quality artifact; remove ambiguity and duplicate work.
3. Define SP-result persistence/versioning if reproducibility or re-use is required.

### Phase 3 — Required for report integration

1. Publish the report field producer-consumer matrix.
2. Supply approved upstream producers for only the needed missing raw measurements.
3. Resolve the legacy `ClinicalReport` versus generated-report lifecycle and identifiers.

### Phase 4 — Required for end-to-end workflow

1. Perform environment-backed integration tests: actual canonical ingest, job polling, Chromium PDF, artifact retrieval, and rollback paths.
2. Add observability for SP failure/fallback, because the adapter intentionally degrades to placeholder results rather than failing the report.

### Phase 5 — Clinical readiness

1. Obtain governed sources and validation for quality score, QT/QTc/SAECG use, thresholds, classifications, flags, and narratives.
2. Implement clinical decision logic only after those sources exist; validate against reference datasets and clinician review.

### Phase 6 — Hardening / production readiness

1. Decide assignment-level versus organization-level doctor access and test all patient/ECG/report endpoints accordingly.
2. Decide token revocation requirements and durable job-queue requirements.
3. Exercise storage, renderer, concurrency, and malformed-input failures in the deployed environment.

## Second-pass verification

Critical/high claims were rechecked against their named source symbols and requirement basis:

- `upload_ecg`, `ingest_ecg`, `create_ecg_record`, `ValidationOrchestrator.validate`, `build_signal_processing_outputs`, `GenerationContextLoader.load`, and `WorkflowOrchestrator.run` exist and participate in the stated call chains.
- The SP integration claim is supported by the active call from `GenerationContextLoader.load`, not by co-location.
- The clinical omission claim is supported by the SP README and explicit `ContextSection.awaiting_signal_processing` construction.
- The viewer disconnect is supported by the viewer imports/use-effects compared against the separately implemented backend waveform route.
- The absence of `NCEP_SP_INTEGRATION_DATA_CONTRACT.md` was checked by repository-wide filename search.

Test execution was not performed because the available bundled Python runtime has no `pytest` package and no repository virtual environment is present. Existing tests were inspected as supporting source evidence, not represented as a successful runtime test run.

## Summary

| Status | Count |
|---|---:|
| Total planned functionalities | 38 |
| Verified working | 23 |
| Partially working | 7 |
| Broken | 0 |
| Not implemented | 1 |
| Not connected | 1 |
| Dead code | 0 |
| Blocked | 0 |
| Clinically unconfirmed | 4 |
| Requirement unclear | 2 |

### Critical blockers

- Clinical classifications, diagnostic flags, interpretations, recommendations, and the formal SP Signal Quality Score must not be represented as clinically ready without governed sources and validation.
- Raw QT/QTc and SAECG values are connected to reports, but their clinical validation basis is absent from this repository.

### High-priority gaps

- Legacy `/upload` creates records that cannot enter report generation.
- The SP contract is code-only and SP results are not persisted.
- Several expected report fields have no producer.
- The ECG viewer is disconnected from waveform retrieval.

### Medium-priority gaps

- Stored NCEP preprocessing is not consumed by reporting/SP.
- Two report persistence models overlap without explicit linkage.
- UI accepted extensions exceed backend parser support.

### Low-priority gaps

- None established from repository evidence.
