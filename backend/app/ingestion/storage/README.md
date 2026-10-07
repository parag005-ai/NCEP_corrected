## Storage Orchestration

Responsibility: Coordinate persistence handoff for ingestion artifacts and normalized ECG records.
Inputs: Normalized `ECGRecord` objects, source references, metadata, and storage requests.
Outputs: Storage orchestration decisions and adapter handoff boundaries.
Dependencies: `storage`, `interfaces`, and ingestion workflow orchestration.
