## Record Builders

Responsibility: Assemble one normalized `ECGRecord` from parsed signal content and separated metadata components.
Inputs: Parsed signal structures, patient metadata, ECG metadata, clinical metadata, device metadata, and validation outcomes.
Outputs: Internal `ECGRecord` domain objects.
Dependencies: `ecg` domain models, metadata extraction, and validation packages.
