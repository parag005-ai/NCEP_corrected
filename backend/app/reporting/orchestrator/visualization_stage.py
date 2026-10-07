"""The visualization pipeline stage (Sprint 3.8 / 3.9 / 4.17).

Adapts the ECG Visualization Engine to the stage contract. The stage owns no
rendering logic -- it delegates to the engine and translates the outcome into
something the orchestrator can act on:

    strip rendered      -> COMPLETED, the stored artifact published for the
                           builders to reference
    nothing drawable    -> SKIPPED, with the reason, so the report section
                           renders a placeholder (Sprint 4.6 / 4.14)
    artifact corrupt    -> FAILED, a critical visualization failure
                           (Sprint 4.20)

Storage failures are not caught here: they are transient by classification
(Sprint 2.13), so they propagate to the orchestrator's retry policy.
"""

from __future__ import annotations

from app.reporting.constants import ArtifactType, PipelineStage, StageStatus
from app.reporting.exceptions import VisualizationError
from app.reporting.models.pending_artifact import PendingReportArtifact
from app.reporting.orchestrator.stage import StageInput, StageResult
from app.reporting.storage.reuse import ArtifactReuseService
from app.reporting.visualizations.engine import ECGVisualizationEngine
from app.reporting.visualizations.rendering_policy import RENDERING_POLICY_VERSION

#: Key under which the stored raw ECG visualization is published to later
#: stages. Absent when no strip could be drawn.
RAW_ECG_ARTIFACT_OUTPUT = "raw_ecg_artifact"

#: Key carrying why no visualization is available, for the placeholder text.
VISUALIZATION_UNAVAILABLE_OUTPUT = "raw_ecg_unavailable_reason"


class GenerateVisualizationsStage:
    """Renders and stores the raw ECG visualization for a report generation.

    A strip already produced for this recording under the same rendering policy
    is carried over rather than drawn again: the recording is immutable and
    rendering is deterministic, so redrawing could only produce the same bytes
    (Sprint 4.21).
    """

    stage = PipelineStage.GENERATE_VISUALIZATIONS

    def __init__(
        self, engine: ECGVisualizationEngine, *, reuse: ArtifactReuseService | None = None
    ) -> None:
        self._engine = engine
        self._reuse = reuse

    def execute(self, payload: StageInput) -> StageResult:
        if payload.context is None:
            return StageResult(
                status=StageStatus.FAILED,
                error_code="MissingGenerationContext",
                error_message="Visualization requires a loaded generation context",
            )

        reused = self._reusable(payload)
        if reused is not None:
            return StageResult(
                status=StageStatus.COMPLETED,
                outputs={RAW_ECG_ARTIFACT_OUTPUT: reused},
                messages=(
                    f"Raw ECG strip reused from artifact "
                    f"{reused.artifact_metadata['reused_from_artifact_id']}",
                ),
            )

        try:
            result = self._engine.generate_raw_ecg(payload.context, job_id=payload.job.id)
        except VisualizationError as exc:
            return StageResult(
                status=StageStatus.FAILED,
                error_code=type(exc).__name__,
                error_message=str(exc),
            )

        if not result.is_available:
            reason = result.unavailable_reason or "no ECG visualization could be generated"
            return StageResult(
                status=StageStatus.SKIPPED,
                outputs={VISUALIZATION_UNAVAILABLE_OUTPUT: reason},
                messages=(f"Raw ECG visualization unavailable: {reason}",),
            )

        artifact = result.artifact
        return StageResult(
            status=StageStatus.COMPLETED,
            outputs={RAW_ECG_ARTIFACT_OUTPUT: artifact},
            messages=(
                f"Raw ECG strip rendered for lead {artifact.artifact_metadata['lead']} "
                f"({artifact.file_size_bytes} bytes)",
            ),
        )

    def _reusable(self, payload: StageInput) -> PendingReportArtifact | None:
        """An equivalent strip from an earlier report version, carried over."""
        if self._reuse is None:
            return None
        return self._reuse.find_reusable(
            ecg_record_id=payload.context.ecg.ecg_record_id,
            artifact_type=ArtifactType.RAW_ECG_SVG,
            policy_version=RENDERING_POLICY_VERSION,
            job_id=payload.job.id,
        )
