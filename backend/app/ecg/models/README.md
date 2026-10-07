## ECG Domain Models

Responsibility: Internal ECG domain object placeholders exchanged across backend modules.
Inputs: Normalized ingestion output and internal transformation pipelines.
Outputs: Domain-level ECG objects such as `ECGRecord`, waveform structures, annotations, and metadata objects.
Dependencies: ECG package contracts and downstream application modules that consume ECG domain objects.
