## Parser Factories

Responsibility: Resolve the appropriate parser contract for a detected ECG source.
Inputs: Detection results, ingestion context, and parser registrations.
Outputs: Parser selections and parser-instantiation boundaries.
Dependencies: Detectors, interfaces, and format-specific parser packages.
