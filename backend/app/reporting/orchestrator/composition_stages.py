"""The report composition pipeline stages (Sprint 3.8 / 6.4).

Two stages, one per report variant, each adapting its builder to the stage
contract. They own no composition logic: they collect what the visualization
stage published, delegate to the builder, and publish the built document for
the Template Engine.

Both stages read the same Generation Context and the same visualization, which
is what keeps the Summary and Detailed reports consistent (Sprint 2.24).

Neither stage writes to the database. The ``GeneratedReport`` row is created
when the report is rendered, which is where its template identity first
exists (approved artifact lifecycle: artifacts stay pending until a report
exists, and are registered only afterwards).
"""

from __future__ import annotations

from app.reporting.builders.report_builders import DetailedReportBuilder, SummaryReportBuilder
from app.reporting.builders.sections import ReportDocument
from app.reporting.constants import PipelineStage, StageStatus
from app.reporting.models.pending_artifact import PendingReportArtifact
from app.reporting.orchestrator.stage import StageInput, StageResult
from app.reporting.orchestrator.visualization_stage import (
    RAW_ECG_ARTIFACT_OUTPUT,
    VISUALIZATION_UNAVAILABLE_OUTPUT,
)

#: Keys under which the built documents are published to the Template Engine.
SUMMARY_DOCUMENT_OUTPUT = "summary_document"
DETAILED_DOCUMENT_OUTPUT = "detailed_document"


def _visualization(payload: StageInput) -> tuple[PendingReportArtifact | None, str | None]:
    """What the visualization stage produced, if it ran and produced anything."""
    published = payload.outputs.get(PipelineStage.GENERATE_VISUALIZATIONS, {})
    return (
        published.get(RAW_ECG_ARTIFACT_OUTPUT),
        published.get(VISUALIZATION_UNAVAILABLE_OUTPUT),
    )


def _describe(document: ReportDocument) -> str:
    available = sum(1 for section in document.sections if section.is_available)
    return (
        f"{document.report_type.value.title()} report composed: "
        f"{available} of {len(document.sections)} sections populated"
    )


class BuildSummaryReportStage:
    """Composes the Summary report document (Sprint 6.7)."""

    stage = PipelineStage.BUILD_SUMMARY_REPORT

    def __init__(self, builder: SummaryReportBuilder | None = None) -> None:
        self._builder = builder or SummaryReportBuilder()

    def execute(self, payload: StageInput) -> StageResult:
        if payload.context is None:
            return StageResult(
                status=StageStatus.FAILED,
                error_code="MissingGenerationContext",
                error_message="Report composition requires a loaded generation context",
            )

        visualization, unavailable_reason = _visualization(payload)
        document = self._builder.build(
            payload.context,
            visualization=visualization,
            visualization_unavailable_reason=unavailable_reason,
        )
        return StageResult(
            status=StageStatus.COMPLETED,
            outputs={SUMMARY_DOCUMENT_OUTPUT: document},
            messages=(_describe(document),),
        )


class BuildDetailedReportStage:
    """Composes the Detailed report document (Sprint 6.8)."""

    stage = PipelineStage.BUILD_DETAILED_REPORT

    def __init__(self, builder: DetailedReportBuilder | None = None) -> None:
        self._builder = builder or DetailedReportBuilder()

    def execute(self, payload: StageInput) -> StageResult:
        if payload.context is None:
            return StageResult(
                status=StageStatus.FAILED,
                error_code="MissingGenerationContext",
                error_message="Report composition requires a loaded generation context",
            )

        visualization, unavailable_reason = _visualization(payload)
        document = self._builder.build(
            payload.context,
            visualization=visualization,
            visualization_unavailable_reason=unavailable_reason,
        )
        return StageResult(
            status=StageStatus.COMPLETED,
            outputs={DETAILED_DOCUMENT_OUTPUT: document},
            messages=(_describe(document),),
        )
