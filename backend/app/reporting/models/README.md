## Reporting Models

Responsibility: Persistent reporting entities (`ReportGenerationJob`, `GeneratedReport`, `ReportArtifact`) and the immutable value objects the subsystem exchanges between its layers.
Inputs: Field values supplied by the reporting repository layer; upstream identifiers (`ecg_record_id`, `patient_id`, `organisation_id`, `requested_by_user_id`) referenced by real foreign keys.
Outputs: Mapped ORM rows registered on the shared `app.database.Base` metadata, plus the `StageExecution`/`JobFailure` execution records and the `ECGArtifactRef`/`ECGArtifactBundle` artifact descriptors.
Dependencies: `app.database`, `app.reporting.constants`, and the upstream `app.models` tables referenced by foreign key.

This is the bottom layer: nothing here imports from `context` or `repositories`, which is what keeps those two packages independent of each other. Reporting never duplicates ECG, patient, doctor or organisation data — it references it.
