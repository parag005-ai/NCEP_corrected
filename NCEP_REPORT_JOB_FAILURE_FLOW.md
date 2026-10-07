# Report Job Failure Flow After the P0 Fix

## Normal path

```text
POST /api/report-generation/jobs
  → persist QUEUED job
  → 202
  → background runner
  → claim RUNNING
  → set current stage
  → LOAD_GENERATION_CONTEXT
       → authorize and validate lineage
       → load artifact bundle with bounded timeout
       → verify manifest/checksums
       → prepare report-time SP context with bounded timeout
  → visualization
  → summary
  → detailed
  → HTML
  → PDF
  → artifact registration
  → COMPLETED
```

## Missing/corrupt artifact

```text
RUNNING
  → LOAD_GENERATION_CONTEXT
  → repository cannot materialize or verify mandatory artifact
  → ECGArtifactUnavailableError
  → stage execution recorded FAILED
  → job FAILED
       failedStage = LOAD_GENERATION_CONTEXT
       errorCode = ECGArtifactUnavailableError
       operator diagnostic retained
       safe client message returned
       completedAt set
  → partial report output cleaned
```

## Timeout

```text
artifact load or report-context SP preparation exceeds configured bound
  → future cancelled where possible
  → ECGArtifactUnavailableError with timeout diagnostic
  → orchestrator records stage failure
  → terminal FAILED
```

Default report-context timeout is 45 seconds and is configurable. Object downloads have a separate bounded timeout.

## Escaped worker exception

```text
Unexpected exception outside normal stage result handling
  → rollback session
  → reload job
  → if non-terminal:
       status = FAILED
       errorCode = REPORT_WORKER_EXCEPTION
       failedStage = current stage when known
       completedAt = now
  → commit
```

## Stale-job protection

```text
GET/list report job
  → status RUNNING?
  → updatedAt older than configured stale interval?
  → mark FAILED
       errorCode = REPORT_JOB_STALE
       failedStage = currentStage
       completedAt = now
```

The default stale interval is 300 seconds. This prevents an abandoned background task from remaining indefinitely `RUNNING` after a process termination.

## Retry behavior

The existing orchestrator retains its stage-attempt policy for exceptions explicitly marked retryable. Permanent artifact absence/integrity failures fail immediately. This repair does not transform missing waveform data into an empty successful report and does not change signal-processing algorithms.

