## Reporting Visualizations

Responsibility: Turn the canonical ECG waveform of a recording into report-ready graphics — Phase 1 renders the raw ECG rhythm strip as SVG.
Inputs: The immutable Generation Context (which references the stored waveform artifact) and the generation job identity.
Outputs: A stored SVG plus a `PendingReportArtifact` describing it (location, size, checksum, lead, time window), or an explicit "unavailable" result with the reason.
Dependencies: `app.reporting.context`, `app.reporting.storage`, `app.reporting.models`, `app.ecg.constants`, numpy.

Pipeline: Waveform Reader → Signal Validator → Lead Selector → Window Selector → SVG Renderer → Artifact Storage.

The engine performs no clinical interpretation, annotates no beats, calculates no parameters and never modifies waveform data. Rendering is deterministic — identical input produces byte-identical SVG. When a recording cannot be drawn faithfully the engine reports it as unavailable rather than drawing an approximation; a corrupt waveform or a renderer failure is critical and raised.
