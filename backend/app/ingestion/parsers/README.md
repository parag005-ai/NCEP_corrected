## Parsers

Responsibility: Organize source-format parser packages and shared parser contracts.
Inputs: Detected format context, validated source files, and parser-specific source bundles.
Outputs: Exactly one normalized internal `ECGRecord` per parser execution.
Dependencies: `interfaces`, `ecg`, shared parser helpers, metadata extraction, and validation orchestration.
