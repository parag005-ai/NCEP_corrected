"""Stage execution value objects recorded in a job's execution history.

Sprint 3.11 requires every pipeline stage to record its name, start time,
completion time, execution duration, execution status, error information,
generated artifacts and execution logs. Sprint 10.13 requires the completed
job to retain that history for debugging and operational monitoring.

These are immutable value objects, not database rows: the history is stored
as a JSON document on the owning ``ReportGenerationJob`` because it is only
ever read as a whole, alongside its job.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.reporting.constants import PipelineStage, StageStatus


@dataclass(frozen=True)
class StageExecution:
    """One execution of one pipeline stage (Sprint 3.11)."""

    stage: PipelineStage
    status: StageStatus
    started_at: datetime
    completed_at: datetime | None = None
    attempt: int = 1
    error_code: str | None = None
    error_message: str | None = None
    artifact_ids: tuple[str, ...] = field(default_factory=tuple)
    messages: tuple[str, ...] = field(default_factory=tuple)

    @property
    def duration_ms(self) -> int | None:
        """Execution duration in milliseconds, or None while the stage is running."""
        if self.completed_at is None:
            return None
        return int((self.completed_at - self.started_at).total_seconds() * 1000)

    def to_dict(self) -> dict:
        """JSON-serializable representation persisted in the job's stage history."""
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "attempt": self.attempt,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "artifact_ids": list(self.artifact_ids),
            "messages": list(self.messages),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StageExecution":
        """Rebuilds a StageExecution from its persisted representation.

        ``duration_ms`` is intentionally not restored: it is derived from the
        timestamps and is persisted only so that stored history stays readable
        without re-deriving it.
        """
        completed_at = data.get("completed_at")
        return cls(
            stage=PipelineStage(data["stage"]),
            status=StageStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
            attempt=data.get("attempt", 1),
            error_code=data.get("error_code"),
            error_message=data.get("error_message"),
            artifact_ids=tuple(data.get("artifact_ids") or ()),
            messages=tuple(data.get("messages") or ()),
        )


@dataclass(frozen=True)
class JobFailure:
    """Why a Report Generation Job stopped (Sprint 10.12 error classification)."""

    code: str
    message: str
    stage: PipelineStage | None = None
