"""Assembly of the Report Generation Pipeline.

One place decides which stages make up a report generation and in which order
(Sprint 3.8). Each subsequent increment appends its stage here as it is
implemented -- visualization, clinical rules, narrative, the two builders,
template rendering, document rendering and artifact storage -- and nothing
else in the subsystem changes.

A pipeline may omit stages that do not exist yet, but never reorder them: the
orchestrator rejects a pipeline whose stages are out of the fixed order.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.reporting.context.loader import GenerationContextLoader
from app.reporting.orchestrator.composition_stages import (
    BuildDetailedReportStage,
    BuildSummaryReportStage,
)
from app.reporting.orchestrator.artifact_stage import StoreReportArtifactsStage
from app.reporting.orchestrator.cleanup import ReportGenerationCleanup
from app.reporting.orchestrator.context_stage import LoadGenerationContextStage
from app.reporting.orchestrator.pdf_stage import GeneratePDFDocumentsStage
from app.reporting.orchestrator.rendering_stage import RenderHTMLDocumentsStage
from app.reporting.orchestrator.stage import ReportPipelineStage
from app.reporting.orchestrator.visualization_stage import GenerateVisualizationsStage
from app.reporting.orchestrator.workflow import WorkflowOrchestrator
from app.reporting.repositories.ecg_artifact_repository import ECGArtifactRepository
from app.reporting.renderers.chromium_renderer import ChromiumPDFRenderer
from app.reporting.renderers.pdf_renderer import PDFRenderer
from app.reporting.storage.artifact_store import ReportArtifactStore
from app.reporting.storage.reuse import ArtifactReuseService
from app.reporting.visualizations.engine import ECGVisualizationEngine


def build_report_pipeline(
    session: Session,
    *,
    ecg_artifacts: ECGArtifactRepository | None = None,
    artifact_store: ReportArtifactStore | None = None,
    pdf_renderer: PDFRenderer | None = None,
) -> tuple[ReportPipelineStage, ...]:
    """The complete Sprint 3.8 pipeline, in execution order."""
    store = artifact_store or ReportArtifactStore()
    renderer = pdf_renderer or ChromiumPDFRenderer()
    return (
        LoadGenerationContextStage(GenerationContextLoader(session, artifacts=ecg_artifacts)),
        GenerateVisualizationsStage(
            ECGVisualizationEngine(store), reuse=ArtifactReuseService(session, store)
        ),
        BuildSummaryReportStage(),
        BuildDetailedReportStage(),
        RenderHTMLDocumentsStage(session, store),
        GeneratePDFDocumentsStage(session, store, renderer),
        StoreReportArtifactsStage(session),
    )


def build_failure_cleanup(
    session: Session, *, artifact_store: ReportArtifactStore | None = None
) -> ReportGenerationCleanup:
    """The rollback the orchestrator applies when a job fails or is cancelled."""
    return ReportGenerationCleanup(session, artifact_store or ReportArtifactStore())


def build_orchestrator(
    session: Session,
    *,
    ecg_artifacts: ECGArtifactRepository | None = None,
    artifact_store: ReportArtifactStore | None = None,
    pdf_renderer: PDFRenderer | None = None,
) -> WorkflowOrchestrator:
    """A fully wired orchestrator: the complete pipeline plus failure rollback.

    This is the construction path production code should use. Building a
    ``WorkflowOrchestrator`` by hand and forgetting the cleanup would leave the
    partial output of a failed run behind, so the safe wiring is assembled here
    once rather than repeated at every call site.
    """
    store = artifact_store or ReportArtifactStore()
    return WorkflowOrchestrator(
        session,
        build_report_pipeline(
            session,
            ecg_artifacts=ecg_artifacts,
            artifact_store=store,
            pdf_renderer=pdf_renderer,
        ),
        cleanup=build_failure_cleanup(session, artifact_store=store),
    )
