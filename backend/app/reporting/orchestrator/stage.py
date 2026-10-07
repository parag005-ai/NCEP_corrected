"""The contract every Report Generation Pipeline stage implements (Sprint 3.22).

    Input      -> the immutable Generation Context, the outputs of the stages
                  that already ran, and the current attempt number.
    Processing -> stage-specific work; artifacts are registered through the
                  Artifact Repository, never carried in the context.
    Output     -> a StageResult: execution status, stage outputs, generated
                  artifact references and execution metadata.

The Workflow Orchestrator interprets the returned status and decides the next
step; a stage never advances the job, never decides retries, and never
modifies the outputs of a stage that ran before it.

Generation Context immutability (approved architecture decision): a stage
receives the context as a read-only input snapshot and must not attempt to
mutate it. Values a later stage needs are returned in ``StageResult.outputs``;
generated documents and images are registered as artifacts and retrieved
through the Artifact Repository.

The contract is a ``Protocol`` rather than a base class so that a stage can be
implemented in whichever package owns its responsibility -- visualization,
rules, builders, rendering -- without that package importing the orchestrator.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.reporting.constants import PipelineStage, StageStatus
from app.reporting.context.generation_context import GenerationContext
from app.reporting.models.documents import freeze_document
from app.reporting.models.generation_job import ReportGenerationJob


@dataclass(frozen=True)
class StageInput:
    """Everything a stage is given to do its work.

    ``context`` is None only for the stage that produces it. ``outputs`` maps
    each already-completed stage to the values it published for later stages.
    ``job`` is provided for identification and lineage; stages must treat it
    as read-only -- only the orchestrator changes a job.
    """

    job: ReportGenerationJob
    attempt: int
    context: GenerationContext | None = None
    outputs: Mapping[PipelineStage, Mapping[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", freeze_document(dict(self.outputs)))


@dataclass(frozen=True)
class StageResult:
    """What a stage reports back to the Workflow Orchestrator (Sprint 3.22).

    ``context`` is set only by the stage that loads the Generation Context;
    every other stage leaves it None and the orchestrator keeps passing the
    context it already holds.
    """

    status: StageStatus
    context: GenerationContext | None = None
    outputs: Mapping[str, Any] = field(default_factory=dict)
    artifact_ids: tuple[str, ...] = field(default_factory=tuple)
    messages: tuple[str, ...] = field(default_factory=tuple)
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", freeze_document(dict(self.outputs)))

    @property
    def should_continue(self) -> bool:
        """Whether the pipeline may proceed to the next stage.

        A completed, partially successful or skipped stage lets the pipeline
        continue with placeholders where data was unavailable (Sprint 3.14
        graceful degradation). A failed or waiting stage stops it.
        """
        return self.status in (StageStatus.COMPLETED, StageStatus.PARTIAL_SUCCESS, StageStatus.SKIPPED)


class ReportPipelineStage(Protocol):
    """One replaceable step of the Report Generation Pipeline."""

    @property
    def stage(self) -> PipelineStage:
        """Which pipeline stage this implementation performs."""

    def execute(self, payload: StageInput) -> StageResult:
        """Performs the stage's work and reports its outcome.

        Raising is equivalent to returning a failed result; the orchestrator
        retries only exceptions that declare themselves retryable.
        """
