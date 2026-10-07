## Reporting Context

Responsibility: Build and hold the immutable Generation Context — the single source of truth consumed by every stage of the Report Generation Pipeline.
Inputs: One `ReportGenerationJob`, and read-only upstream data (Organisation, Patient, Doctor, ECG record, canonical ECG artifacts). Signal Processing outputs join in Phase 2.
Outputs: One frozen `GenerationContext` per report generation, with explicit placeholders for every section whose data source is not yet integrated.
Dependencies: `app.models` (upstream rows), `app.security` (ownership rules), `app.reporting.repositories`, `app.reporting.constants`, `app.reporting.exceptions`.

The loader enforces tenant safety itself: it re-resolves upstream records from the ECG recording, re-checks the requester's access, and refuses inconsistent lineage. No downstream stage queries an upstream module again.
