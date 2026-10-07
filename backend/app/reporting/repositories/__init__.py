"""Reporting repository package (Sprint 2.18).

Abstracts every data access of the Report Generation subsystem away from its
business logic:

    Workflow Orchestrator -> Report Repository -> Database
                          -> ECG Artifact Repository -> ECG artifact store

No business logic is implemented here. Repositories record decisions; they do
not make them. The database repositories take the SQLAlchemy ``Session`` they
operate on, flush so constraint violations surface immediately, and never
commit -- the caller owns the transaction boundary.
``ECGArtifactRepository`` is read-only: reporting consumes upstream artifacts
and never modifies them.
"""

from app.reporting.repositories.artifact_repository import ReportArtifactRepository
from app.reporting.repositories.ecg_artifact_repository import ECGArtifactRepository
from app.reporting.repositories.job_repository import ReportGenerationJobRepository
from app.reporting.repositories.report_repository import GeneratedReportRepository

__all__ = [
    "ECGArtifactRepository",
    "GeneratedReportRepository",
    "ReportArtifactRepository",
    "ReportGenerationJobRepository",
]
