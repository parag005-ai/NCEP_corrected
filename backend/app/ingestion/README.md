## Ingestion Package

Responsibility: Detect, validate, parse, normalize, and stage incoming ECG sources into one internal `ECGRecord`.
Inputs: Uploaded files, file bundles, source metadata, and ingestion configuration.
Outputs: One normalized `ECGRecord`, separated metadata objects, validation results, and storage orchestration handoff.
Dependencies: `ecg`, `interfaces`, parser packages, metadata extraction packages, validation packages, and storage orchestration.
