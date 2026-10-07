## Reporting Package

Responsibility: Generate versioned Summary and Detailed clinical reports from an already ingested ECG recording (orchestration, visualization, composition, rendering, artifact management, versioning).
Inputs: `ecg_record_id` plus the authenticated caller's identity; upstream data is read through the Authentication, Patient, Doctor, Organisation, ECG Ingestion and (Phase 2) Signal Processing modules.
Outputs: Report generation jobs, immutable versioned generated reports, and registered report artifacts (Summary/Detailed HTML and PDF, ECG SVG, metadata, manifest).
Dependencies: `database`, `models` (upstream ORM rows), `ecg`, `storage`, and the shared configuration/security modules. No upstream module depends on this package.

`ecg_record_id` is the primary integration key across every reporting entity — reports belong to a recording, never to a patient in general.
