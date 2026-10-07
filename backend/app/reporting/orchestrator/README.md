## Reporting Orchestrator

Responsibility: Control report generation — create jobs, execute pipeline stages in the fixed Sprint 3.8 order, track progress, record stage history, apply the retry policy, handle failures, and finalize job state.
Inputs: A report generation request (`ecg_record_id` plus the requesting identity) and the ordered pipeline stages assembled in `pipeline.py`.
Outputs: A persisted `ReportGenerationJob` advanced through its lifecycle, with per-stage execution history and progress.
Dependencies: `app.reporting.repositories` (job persistence), `app.reporting.context` (the stage it currently drives), `app.reporting.constants`, `app.reporting.exceptions`.

The orchestrator contains no clinical logic and performs no visualization, composition or rendering. It never mutates the Generation Context: stages receive it as a read-only snapshot, publish values for later stages via `StageResult.outputs`, and register generated documents with the Artifact Repository. Only the orchestrator changes a job's state, and only through the `JobStateMachine`.

Execution is synchronous; scheduling it onto a background worker belongs to the API layer.
