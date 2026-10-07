## Reporting Storage

Responsibility: Persist and locate the bytes of generated report artifacts (ECG SVGs now; HTML and PDF documents once those stages exist).
Inputs: Artifact bytes plus the `ecg_record_id` and `job_id` that produced them.
Outputs: `StoredArtifact` descriptors carrying the storage location, measured file size and SHA-256 checksum.
Dependencies: `app.config` (storage root), `app.reporting.exceptions`.

Layout is `<root>/<ecg_record_id>/<job_id>/<relative_path>` — job-scoped, because a stage writes its output before the report version that will own it exists. The store knows nothing about the `ReportArtifact` registry, so the backend can change without touching the registry.
