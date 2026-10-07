"""Report Generation Job state machine (Sprint 3.12 / 10.6).

    Requested -> Queued -> Running -> Completed
                              |
                              +-> Waiting for Signal Processing
                              +-> Failed
                              +-> Cancelled

State transitions are controlled exclusively by the Workflow Orchestrator.
This module holds the transition table and the guard that enforces it; it
performs no persistence and no execution -- it only answers whether a move is
legal, so that an illegal move fails loudly instead of corrupting a job's
recorded history.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.reporting.constants import JobStatus
from app.reporting.exceptions import InvalidJobTransitionError

#: The only job state changes the orchestrator may make. A state absent from a
#: value set is unreachable from that state; terminal states have none.
ALLOWED_TRANSITIONS: Mapping[JobStatus, frozenset[JobStatus]] = {
    JobStatus.REQUESTED: frozenset({JobStatus.QUEUED, JobStatus.CANCELLED, JobStatus.FAILED}),
    JobStatus.QUEUED: frozenset({JobStatus.RUNNING, JobStatus.CANCELLED, JobStatus.FAILED}),
    JobStatus.RUNNING: frozenset(
        {
            JobStatus.WAITING_FOR_SIGNAL_PROCESSING,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }
    ),
    # A waiting job resumes execution once its Signal Processing inputs arrive.
    JobStatus.WAITING_FOR_SIGNAL_PROCESSING: frozenset(
        {JobStatus.RUNNING, JobStatus.CANCELLED, JobStatus.FAILED}
    ),
    JobStatus.COMPLETED: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}

#: States after which a job never executes again.
TERMINAL_STATUSES: frozenset[JobStatus] = frozenset(
    status for status, targets in ALLOWED_TRANSITIONS.items() if not targets
)


class JobStateMachine:
    """Guards every transition of a Report Generation Job's lifecycle."""

    @staticmethod
    def is_terminal(status: JobStatus) -> bool:
        """True when the job has finished and may never execute again."""
        return status in TERMINAL_STATUSES

    @staticmethod
    def can_transition(current: JobStatus, target: JobStatus) -> bool:
        """Whether the orchestrator may move a job from ``current`` to ``target``."""
        return target in ALLOWED_TRANSITIONS.get(current, frozenset())

    @classmethod
    def validate(cls, current: JobStatus, target: JobStatus) -> None:
        """Raises ``InvalidJobTransitionError`` unless the transition is legal."""
        if not cls.can_transition(current, target):
            raise InvalidJobTransitionError(
                f"A report generation job may not move from {current.value} to {target.value}"
            )
