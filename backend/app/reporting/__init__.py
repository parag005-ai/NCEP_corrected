"""Report Generation subsystem.

Responsibility (Sprint 2.4 / 3.23): orchestration, ECG visualization, report
composition, template rendering, HTML generation, PDF generation, artifact
management, and report versioning.

This subsystem is a strict *consumer* of the upstream NCEP modules
(Authentication, Organisation, Doctor, Patient, ECG Ingestion, Signal
Processing). It never parses ECG files, never computes clinical parameters,
never authenticates users, and never modifies upstream data (Sprint 3.24).

The package is built incrementally in the order defined by the Sprint
document; only the components required by the increments delivered so far
are present.
"""
