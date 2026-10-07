## Reporting Repositories

Responsibility: All data access for the Report Generation subsystem — job creation and execution state, report versioning and history, report artifact registration and lifecycle, and read-only access to the canonical ECG artifacts of a recording.
Inputs: A SQLAlchemy `Session` (database repositories) or an ECG artifact store (`ECGArtifactRepository`), plus already-validated, already-authorized values from the Workflow Orchestrator, Context Loader or API layer.
Outputs: Persisted `ReportGenerationJob`, `GeneratedReport` and `ReportArtifact` rows; resolved `ECGArtifactBundle` descriptors and documents.
Dependencies: `app.reporting.models`, `app.reporting.context`, `app.reporting.constants`, `app.reporting.exceptions`, `app.storage`, `app.models`, SQLAlchemy.

Repositories contain no business logic: they never validate state transitions, decide retries, or choose the next stage. Database repositories flush and never commit — the caller owns the transaction boundary. `ECGArtifactRepository` only reads: reporting never parses, preprocesses or modifies upstream ECG artifacts.
