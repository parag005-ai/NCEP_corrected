"""Workflow Orchestrator package (Sprint 3.5 / 3.12 / 10.7).

The central controller of report generation: it creates jobs, drives them
through the fixed stage order, records progress and stage history, applies the
retry policy, and finalizes each job's state. It holds no clinical logic and
performs no rendering.

Stages are injected, so this package never imports a domain module beyond the
context loader it already orchestrates, and later increments extend the
pipeline in ``pipeline.py`` alone.
"""

from app.reporting.orchestrator.composition_stages import (
    DETAILED_DOCUMENT_OUTPUT,
    SUMMARY_DOCUMENT_OUTPUT,
    BuildDetailedReportStage,
    BuildSummaryReportStage,
)
from app.reporting.orchestrator.artifact_stage import StoreReportArtifactsStage
from app.reporting.orchestrator.cleanup import JobFailureCleanup, ReportGenerationCleanup
from app.reporting.orchestrator.context_stage import LoadGenerationContextStage
from app.reporting.orchestrator.pdf_stage import GeneratePDFDocumentsStage
from app.reporting.orchestrator.pipeline import (
    build_failure_cleanup,
    build_orchestrator,
    build_report_pipeline,
)
from app.reporting.orchestrator.rendering_stage import (
    GENERATED_REPORT_OUTPUT,
    RenderHTMLDocumentsStage,
)
from app.reporting.orchestrator.stage import ReportPipelineStage, StageInput, StageResult
from app.reporting.orchestrator.state_machine import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATUSES,
    JobStateMachine,
)
from app.reporting.orchestrator.visualization_stage import (
    RAW_ECG_ARTIFACT_OUTPUT,
    VISUALIZATION_UNAVAILABLE_OUTPUT,
    GenerateVisualizationsStage,
)
from app.reporting.orchestrator.workflow import DEFAULT_MAX_STAGE_ATTEMPTS, WorkflowOrchestrator

__all__ = [
    "ALLOWED_TRANSITIONS",
    "DEFAULT_MAX_STAGE_ATTEMPTS",
    "DETAILED_DOCUMENT_OUTPUT",
    "SUMMARY_DOCUMENT_OUTPUT",
    "BuildDetailedReportStage",
    "BuildSummaryReportStage",
    "GENERATED_REPORT_OUTPUT",
    "GeneratePDFDocumentsStage",
    "JobFailureCleanup",
    "ReportGenerationCleanup",
    "build_failure_cleanup",
    "build_orchestrator",
    "GenerateVisualizationsStage",
    "StoreReportArtifactsStage",
    "RenderHTMLDocumentsStage",
    "JobStateMachine",
    "LoadGenerationContextStage",
    "RAW_ECG_ARTIFACT_OUTPUT",
    "ReportPipelineStage",
    "StageInput",
    "StageResult",
    "TERMINAL_STATUSES",
    "VISUALIZATION_UNAVAILABLE_OUTPUT",
    "WorkflowOrchestrator",
    "build_report_pipeline",
]
