## Format Detection

Responsibility: Identify ingestion source formats using metadata, headers, manifests, and binary/container signatures.
Inputs: Uploaded files, bundles, and source inspection context.
Outputs: Format detection outcomes used by parser selection.
Dependencies: Parser factory orchestration and low-level source inspection utilities.
