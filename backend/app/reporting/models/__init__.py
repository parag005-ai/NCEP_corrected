"""Reporting model package.

Holds the three persistent reporting entities defined by Sprint 2.17 --
``ReportGenerationJob``, ``GeneratedReport`` and ``ReportArtifact`` -- plus
the immutable value objects the subsystem exchanges between its layers.
Downstream modules should import from here rather than reaching into
individual submodules.

This is the bottom layer of the subsystem: nothing here imports from
``context`` or ``repositories``, which is what keeps those two packages
independent of each other.

Importing this package registers the reporting tables on the shared
``app.database.Base`` metadata used by Alembic.
"""

from app.reporting.models.documents import freeze_document
from app.reporting.models.ecg_artifacts import ECGArtifactBundle, ECGArtifactRef
from app.reporting.models.execution import JobFailure, StageExecution
from app.reporting.models.generated_report import GeneratedReport
from app.reporting.models.generation_job import ReportGenerationJob
from app.reporting.models.identifiers import new_artifact_id, new_job_id, new_report_id
from app.reporting.models.pending_artifact import PendingReportArtifact
from app.reporting.models.report_artifact import ReportArtifact

__all__ = [
    "ECGArtifactBundle",
    "ECGArtifactRef",
    "GeneratedReport",
    "JobFailure",
    "PendingReportArtifact",
    "ReportArtifact",
    "ReportGenerationJob",
    "StageExecution",
    "freeze_document",
    "new_artifact_id",
    "new_job_id",
    "new_report_id",
]
