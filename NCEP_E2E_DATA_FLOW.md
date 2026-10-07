# NCEP End-to-End Data Flow and Breakpoints

## Actual production path tested

```text
Doctor browser
  -> POST /api/ecg-records/ingest
  -> Netlify proxy
  -> Render FastAPI ingest_ecg
  -> UploadOrchestrator / create_ecg_record
  -> WFDB format detector
  -> WFDB parser (.hea resolves .dat + .xyz)
  -> MetadataOrchestrator
  -> ValidationOrchestrator
  -> ECGRecordBuilder
  -> FilesystemArtifactStore.store
       -> local canonical files
       -> best-effort Cloudinary backup
  -> PreprocessingOrchestrator
  -> database ECGRecord commit
  -> response to browser
```

### Observed break A: response lifecycle

The browser uploaded all bytes and reached 100%, but the proxied request returned 504. The backend subsequently exposed `ecg-ed314afc`, proving that processing/commit continued beyond the client-visible timeout.

```text
backend commit succeeds
          X
browser never receives record identity
```

This breaks idempotency and retry safety. It also prevents the UI from reliably advancing to the next workflow step.

## Canonical record outputs observed

```text
ecg-ed314afc
  canonical recordId: ae4d60a2-9c5d-4783-a82a-1da59b922d65
  format: WFDB
  rate: 1000 Hz
  samples: 115200
  duration: 115.2 s
  leads: 15 (12-lead + X/Y/Z)
  validation: WARNING
  ingestion quality: 0.120720245446648 / low_snr
  ingestion beatCount: 139
```

## Waveform/viewer path

```text
Frontend viewer
  -X-> canonical waveform endpoint (no production wiring found)

GET /api/ecg-records/ecg-ed314afc/waveform
  -> read ECGRecord.storage_path
  -> os.path.exists(local path)
  -X-> 404 No waveform file for this record
```

### Observed break B: artifact durability

The database row exists while the waveform file does not. The route bypasses the repository hydration abstraction and assumes a live local filesystem path. On an ephemeral deployment, that assumption is not durable.

## Report-generation path

```text
POST /api/report-generation/jobs
  -> job rgj-1294b55f04b4 (QUEUED)
  -> BackgroundTasks / run_generation_job
  -> WorkflowOrchestrator
  -> LoadGenerationContextStage
  -> GenerationContextLoader.load
  -> ECGArtifactRepository.load_bundle
  -> FilesystemArtifactStore.hydrate
  -X-> job remains RUNNING, progress 0, LOAD_GENERATION_CONTEXT

Not reached:
  -> build_signal_processing_outputs
  -> WaveformReader
  -> analyze_waveform
  -> summary/detailed report builders
  -> HTML renderer
  -> PDF renderer
  -> report artifact registration/retrieval
```

The job's exact internal wait or exception was not observable. Given the verified missing local waveform and the stage's repository/hydration call, artifact recovery is the most likely blocked operation. The orchestration defect is independently established: a worker stage must be bounded and must transition to `FAILED` instead of remaining indefinitely `RUNNING` with zero progress.

## Preprocessing split

```text
Ingest path:
  canonical waveform -> PreprocessingOrchestrator -> quality/beat metadata

Report path:
  canonical raw bundle -> report SP builder -> preprocessing + analyze_waveform
```

The report path does not consume the ingestion preprocessing artifact. This permits algorithm/version/parameter drift and makes identical-record reproducibility harder to guarantee.

## Required target state

```text
Browser
  -> create idempotent ingest job (fast 202)
  -> poll/subscribe to terminal ingest state
  -> receive canonical ECG ID

Ingest worker
  -> parse and validate
  -> write artifacts to durable object storage
  -> verify checksums and required artifact manifest
  -> transactionally commit record + manifest
  -> terminal SUCCEEDED or FAILED

All waveform consumers
  -> ArtifactRepository
  -> durable storage (with bounded local cache/hydration)

Report worker
  -> bounded context load
  -> versioned SP inputs/parameters/outputs
  -> summary/detailed/HTML/PDF
  -> durable report artifacts
  -> terminal COMPLETED or FAILED
```

## Source trace anchors

- Upload page: `NCEPfrontend/src/app/doctor/ecg-upload/page.tsx`
- Frontend ECG service: `NCEPfrontend/src/services/ecg.service.ts`
- Ingest and waveform routes: `backend/app/routers/ecg.py`
- Canonical creation: `backend/app/ingestion/record_creator.py`
- Filesystem/object backup: `backend/app/storage/file/filesystem.py`, `backend/app/storage/file/cloudinary_backup.py`
- Report context loading: `backend/app/reporting/context/loader.py`
- Report SP mapping: `backend/app/reporting/context/signal_processing_builder.py`
- Report workflow: `backend/app/reporting/orchestrator/pipeline.py`

