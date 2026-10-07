"""The first pipeline stage: load the Generation Context (Sprint 3.8 / 3.9).

Adapts the Generation Context Loader to the pipeline stage contract. The stage
owns no loading logic of its own -- it delegates to the loader and translates
its outcome into a ``StageResult`` the orchestrator can act on.

Every failure the loader raises is a critical failure (Sprint 2.12 / 3.14):
without a context there is nothing to build a report from, so none of them are
retryable and the orchestrator terminates the job.
"""

from __future__ import annotations

from app.reporting.constants import PipelineStage, StageStatus
from app.reporting.context.loader import GenerationContextLoader
from app.reporting.exceptions import ContextLoadError, ReportAccessDeniedError
from app.reporting.orchestrator.stage import StageInput, StageResult


class LoadGenerationContextStage:
    """Builds the immutable Generation Context the rest of the pipeline reads."""

    stage = PipelineStage.LOAD_GENERATION_CONTEXT

    def __init__(self, loader: GenerationContextLoader) -> None:
        self._loader = loader

    def execute(self, payload: StageInput) -> StageResult:
        try:
            context = self._loader.load(payload.job)
        except (ContextLoadError, ReportAccessDeniedError) as exc:
            return StageResult(
                status=StageStatus.FAILED,
                error_code=type(exc).__name__,
                error_message=str(exc),
            )

        return StageResult(
            status=StageStatus.COMPLETED,
            context=context,
            messages=(
                f"Generation context loaded for report version {context.generation.report_version}",
            ),
        )
