## Validation

Responsibility: Organize independent validators across format, file, signal, metadata, and quality concerns.
Inputs: Source files, extracted metadata, waveform content, and ingestion context.
Outputs: Validation outcomes used to accept, reject, or flag ingestion payloads.
Dependencies: `ecg`, metadata extraction, parser orchestration, and validation interface contracts.
