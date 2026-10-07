"""Shared reporting enumerations and version constants.

This module is the vocabulary of the Report Generation subsystem: the job
state machine (Sprint 3.12 / 10.6), the fixed pipeline stage order (Sprint
3.8 / 3.13), the per-stage execution states (Sprint 3.11 / 2.9), the report
lifecycle (Sprint 10.18) and the artifact taxonomy/lifecycle (Sprint 9.6 /
9.8).

No business logic belongs here -- only names and versions. Which state
transitions are *legal* is decided exclusively by the Workflow Orchestrator
(Sprint 3.12), not by this module and not by the repository layer.

Enumerations are ``str`` enums and are persisted by value, matching the
convention used by ``app.ecg.constants``.
"""

from __future__ import annotations

from enum import Enum

# ---------------------------------------------------------------------------
# Provenance versions (Sprint 3.18 / 9.9 / 10.22)
#
# Every generated report records the versions below so that a historical
# report can be reproduced and audited. They are bumped deliberately when the
# pipeline, the persisted report package schema, or the subsystem itself
# changes in a way that alters generated output.
# ---------------------------------------------------------------------------

#: Version of the report generation pipeline (stage set and stage semantics).
REPORT_PIPELINE_VERSION = "1.0.0"

#: Version of the persisted report package schema (report + artifact layout).
REPORT_SCHEMA_VERSION = "1.0.0"

#: Version of the Report Generation subsystem itself.
REPORTING_SOFTWARE_VERSION = "ncep-reporting-1.0.0"


class JobStatus(str, Enum):
    """Lifecycle states of a Report Generation Job (Sprint 3.12 / 10.6).

    Only the Workflow Orchestrator transitions a job between these states.
    """

    REQUESTED = "REQUESTED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOR_SIGNAL_PROCESSING = "WAITING_FOR_SIGNAL_PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PipelineStage(str, Enum):
    """The stages of the Report Generation Pipeline (Sprint 3.8 / 3.13).

    Members are declared in the fixed execution order defined by Sprint 3.8.
    """

    LOAD_GENERATION_CONTEXT = "LOAD_GENERATION_CONTEXT"
    GENERATE_VISUALIZATIONS = "GENERATE_VISUALIZATIONS"
    EVALUATE_CLINICAL_RULES = "EVALUATE_CLINICAL_RULES"
    GENERATE_NARRATIVE = "GENERATE_NARRATIVE"
    BUILD_SUMMARY_REPORT = "BUILD_SUMMARY_REPORT"
    BUILD_DETAILED_REPORT = "BUILD_DETAILED_REPORT"
    RENDER_HTML_DOCUMENTS = "RENDER_HTML_DOCUMENTS"
    GENERATE_PDF_DOCUMENTS = "GENERATE_PDF_DOCUMENTS"
    STORE_REPORT_ARTIFACTS = "STORE_REPORT_ARTIFACTS"


class StageStatus(str, Enum):
    """Execution state of a single pipeline stage (Sprint 3.11 / 2.9)."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    SKIPPED = "SKIPPED"
    WAITING = "WAITING"
    FAILED = "FAILED"


class ReportStatus(str, Enum):
    """Lifecycle states of a Generated Report (Sprint 10.18).

    The Sprint lifecycle begins at ``Requested``; that state is carried by the
    owning ``ReportGenerationJob`` (``JobStatus.REQUESTED``). A
    ``GeneratedReport`` row is only created once its version and template
    provenance is known, so report-level state begins at ``GENERATING``.
    """

    GENERATING = "GENERATING"
    RENDERED = "RENDERED"
    STORED = "STORED"
    AVAILABLE = "AVAILABLE"
    FAILED = "FAILED"


class ReportType(str, Enum):
    """The two report variants generated from one Generation Context (Sprint 2).

    Both present identical clinical data; they differ in depth and template.
    """

    SUMMARY = "SUMMARY"
    DETAILED = "DETAILED"


class SectionStatus(str, Enum):
    """Availability of one data-driven report section (Sprint 3.15 / 5.7 / 6.16).

    The subsystem follows a strict No Fabrication Policy: a section whose data
    source is not yet connected is marked explicitly rather than filled with
    estimated values.
    """

    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    AWAITING_SIGNAL_PROCESSING = "AWAITING_SIGNAL_PROCESSING"


#: Standardized placeholder shown for sections that depend on the Signal
#: Processing module, which is not integrated during Phase 1.
PLACEHOLDER_AWAITING_SIGNAL_PROCESSING = "Awaiting Signal Processing Results"

#: Standardized placeholder for a value that is simply absent from the source
#: data. Never a substitute for a value that exists (Sprint 3.15).
PLACEHOLDER_NOT_AVAILABLE = "—"


class ArtifactType(str, Enum):
    """Generated report assets managed by the Artifact Repository (Sprint 9.6).

    Phase 2/3 visualization artifacts (annotated ECG, QT, SAECG, ...) are added
    to this enumeration when the corresponding visualization modules are built.
    """

    #: The Summary Report is delivered as structured data: its presentation
    #: belongs to the frontend, so no Summary HTML or PDF is generated.
    SUMMARY_JSON = "SUMMARY_JSON"
    SUMMARY_HTML = "SUMMARY_HTML"
    DETAILED_HTML = "DETAILED_HTML"
    SUMMARY_PDF = "SUMMARY_PDF"
    DETAILED_PDF = "DETAILED_PDF"
    RAW_ECG_SVG = "RAW_ECG_SVG"
    METADATA_JSON = "METADATA_JSON"
    MANIFEST_JSON = "MANIFEST_JSON"


class ArtifactStatus(str, Enum):
    """Artifact lifecycle states (Sprint 9.8 / 4.16).

    An artifact becomes immutable once it reaches ``REGISTERED``.
    """

    GENERATED = "GENERATED"
    VALIDATED = "VALIDATED"
    REGISTERED = "REGISTERED"
    STORED = "STORED"
    AVAILABLE = "AVAILABLE"
    ARCHIVED = "ARCHIVED"


__all__ = [
    "PLACEHOLDER_AWAITING_SIGNAL_PROCESSING",
    "PLACEHOLDER_NOT_AVAILABLE",
    "REPORT_PIPELINE_VERSION",
    "REPORT_SCHEMA_VERSION",
    "REPORTING_SOFTWARE_VERSION",
    "ArtifactStatus",
    "ArtifactType",
    "JobStatus",
    "PipelineStage",
    "ReportStatus",
    "ReportType",
    "SectionStatus",
    "StageStatus",
]
