"""Exception hierarchy for the Report Generation subsystem.

Mirrors the convention established by ``app.ingestion.exceptions``: every
failure inside the subsystem is raised explicitly rather than returned as an
ambiguous result, carries the pipeline stage it originated from, and
propagates outward to the service/API layer which translates it into a REST
response. No report artifact is ever exposed when one of these is raised.

The hierarchy grows with the subsystem; only the exceptions raised by the
components implemented so far are defined here.
"""

from __future__ import annotations


class ReportingError(Exception):
    """Base class for every error raised by the Report Generation subsystem."""

    stage: str = "reporting"

    #: Whether the Workflow Orchestrator may retry the failed stage.
    #: Failures are permanent unless a subclass declares otherwise, so a bug
    #: is never retried into an infinite loop (Sprint 3.16 / 2.13).
    retryable: bool = False


class TransientReportingError(ReportingError):
    """Base class for failures a stage may recover from by retrying.

    Sprint 2.13 / 3.16 limit retries to transient infrastructure conditions --
    database timeouts, temporary storage failures, network interruptions and
    internal service timeouts. Missing artifacts, invalid records, invalid
    contexts and rendering errors are never retried.
    """

    retryable = True


# ---------------------------------------------------------------------------
# Persistence layer errors
# ---------------------------------------------------------------------------


class ReportRepositoryError(ReportingError):
    """Base class for failures raised by the reporting repository layer."""

    stage = "persistence"


class ReportJobNotFoundError(ReportRepositoryError):
    """Raised when a Report Generation Job is required but does not exist."""


class GeneratedReportNotFoundError(ReportRepositoryError):
    """Raised when a Generated Report is required but does not exist."""


class ReportArtifactNotFoundError(ReportRepositoryError):
    """Raised when a Report Artifact is required but does not exist."""


# ---------------------------------------------------------------------------
# Authorization errors
# ---------------------------------------------------------------------------


class ReportAccessDeniedError(ReportingError):
    """Raised when the requesting user may not access the requested recording.

    Reporting does not implement its own authentication (Sprint 10.10): it
    re-checks the platform's ownership rules against persisted state so no
    caller can reach report data outside its tenant.
    """

    stage = "authorization"


# ---------------------------------------------------------------------------
# Generation Context errors (Sprint 2.12 / 3.14 -- all critical failures)
# ---------------------------------------------------------------------------


class ContextLoadError(ReportingError):
    """Base class for failures that prevent a Generation Context being built.

    Every subclass is a critical failure: the pipeline terminates and no
    partial report is exposed.
    """

    stage = "context_loading"


class ECGRecordNotFoundError(ContextLoadError):
    """Raised when the ECG recording a report was requested for does not exist."""


class UpstreamRecordMissingError(ContextLoadError):
    """Raised when a mandatory upstream record (organisation, patient, user) is absent."""


class InconsistentContextError(ContextLoadError):
    """Raised when the upstream records do not agree with each other.

    Guards against a report ever presenting one patient's or tenant's data
    under another's identity (Sprint 5.12 consistency validation, 5.13
    Category 3).
    """


class ECGArtifactUnavailableError(ContextLoadError):
    """Raised when the canonical ECG artifacts cannot be read for a recording.

    Sprint 2.12/3.14 classify unreadable or absent required ECG artifacts as a
    critical failure. Reporting never re-parses source ECG files to work
    around missing artifacts -- parsing belongs to ECG Ingestion.
    """


# ---------------------------------------------------------------------------
# Visualization and artifact storage errors
# ---------------------------------------------------------------------------


class VisualizationError(ReportingError):
    """Base class for failures of the ECG Visualization Engine."""

    stage = "visualization"


class WaveformReadError(VisualizationError):
    """Raised when a canonical waveform artifact cannot be read or is corrupt.

    Sprint 4.20 classifies an unlocatable or corrupt waveform artifact as a
    critical visualization failure. A signal that is *readable but unusable*
    is not this error -- that produces an explicit placeholder instead
    (Sprint 4.6 / 4.7).
    """


class SVGRenderingError(VisualizationError):
    """Raised when the SVG renderer cannot produce a visualization."""


class TemplateError(ReportingError):
    """Base class for failures of the Template Engine.

    Sprint 2.13 / 3.16 classify template and rendering errors as permanent:
    retrying a template that cannot be loaded or bound never succeeds.
    """

    stage = "template_rendering"


class TemplateNotFoundError(TemplateError):
    """Raised when an approved template is not registered or its file is missing."""


class TemplateRenderingError(TemplateError):
    """Raised when a template cannot be bound to a report document."""


class PDFRenderingError(ReportingError):
    """Raised when the report HTML could not be converted into a PDF.

    Sprint 9.14 classifies PDF generation failure as critical: no report is
    published from a document that could not be rendered.
    """

    stage = "document_rendering"


class ArtifactIntegrityError(ReportingError):
    """Raised when a stored artifact does not match what the registry records.

    Only verified artifacts are made available to downstream consumers
    (Sprint 9.11).
    """

    stage = "artifact_management"


class InvalidArtifactTransitionError(ReportingError):
    """Raised on an attempt to move an artifact into a state it may not enter.

    Artifacts are immutable once registered; only their lifecycle status
    advances, and only along the declared path (Sprint 9.8).
    """

    stage = "artifact_management"


class ReportArtifactStorageError(TransientReportingError):
    """Raised when a generated report artifact cannot be persisted.

    Classified as transient because Sprint 2.13 makes temporary storage
    failures retryable; a genuinely permanent condition simply exhausts the
    orchestrator's bounded retries.
    """

    stage = "artifact_storage"


# ---------------------------------------------------------------------------
# Orchestration errors
# ---------------------------------------------------------------------------


class OrchestrationError(ReportingError):
    """Base class for failures in the control of the report generation pipeline."""

    stage = "orchestration"


class InvalidJobTransitionError(OrchestrationError):
    """Raised on an attempt to move a job into a state it may not enter.

    Job state transitions are controlled exclusively by the Workflow
    Orchestrator (Sprint 3.12); this error is what makes "exclusively"
    enforceable rather than merely documented.
    """


class ConcurrentJobExecutionError(OrchestrationError):
    """Raised when a job is already being executed by another worker.

    Execution is claimed with a single conditional update, so only one runner
    can ever drive a job; a second would otherwise duplicate its documents and
    its report version.
    """


class PipelineDefinitionError(OrchestrationError):
    """Raised when a pipeline is assembled from an invalid set of stages.

    The stage execution order is fixed (Sprint 3.8): a pipeline may omit
    stages that are not yet implemented, but it may never reorder or repeat
    them.
    """


__all__ = [
    "ArtifactIntegrityError",
    "ConcurrentJobExecutionError",
    "ContextLoadError",
    "ECGArtifactUnavailableError",
    "ECGRecordNotFoundError",
    "GeneratedReportNotFoundError",
    "InconsistentContextError",
    "InvalidArtifactTransitionError",
    "InvalidJobTransitionError",
    "OrchestrationError",
    "PDFRenderingError",
    "PipelineDefinitionError",
    "ReportAccessDeniedError",
    "ReportArtifactNotFoundError",
    "ReportArtifactStorageError",
    "ReportJobNotFoundError",
    "ReportRepositoryError",
    "ReportingError",
    "SVGRenderingError",
    "TemplateError",
    "TemplateNotFoundError",
    "TemplateRenderingError",
    "TransientReportingError",
    "UpstreamRecordMissingError",
    "VisualizationError",
    "WaveformReadError",
]
