"""Tests for the Report Generation Job state machine (Sprint 3.12)."""

from __future__ import annotations

import pytest

from app.reporting.constants import JobStatus
from app.reporting.exceptions import InvalidJobTransitionError
from app.reporting.orchestrator import ALLOWED_TRANSITIONS, TERMINAL_STATUSES, JobStateMachine


def test_the_sprint_lifecycle_is_walkable_end_to_end():
    assert JobStateMachine.can_transition(JobStatus.REQUESTED, JobStatus.QUEUED)
    assert JobStateMachine.can_transition(JobStatus.QUEUED, JobStatus.RUNNING)
    assert JobStateMachine.can_transition(JobStatus.RUNNING, JobStatus.COMPLETED)


def test_a_running_job_may_wait_fail_or_be_cancelled():
    for target in (JobStatus.WAITING_FOR_SIGNAL_PROCESSING, JobStatus.FAILED, JobStatus.CANCELLED):
        assert JobStateMachine.can_transition(JobStatus.RUNNING, target)


def test_a_waiting_job_resumes_into_running():
    assert JobStateMachine.can_transition(JobStatus.WAITING_FOR_SIGNAL_PROCESSING, JobStatus.RUNNING)


def test_terminal_states_are_final():
    assert TERMINAL_STATUSES == {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
    for status in TERMINAL_STATUSES:
        assert JobStateMachine.is_terminal(status)
        assert ALLOWED_TRANSITIONS[status] == frozenset()


def test_skipping_the_queue_is_refused():
    assert not JobStateMachine.can_transition(JobStatus.REQUESTED, JobStatus.RUNNING)

    with pytest.raises(InvalidJobTransitionError, match="REQUESTED to RUNNING"):
        JobStateMachine.validate(JobStatus.REQUESTED, JobStatus.RUNNING)


def test_a_finished_job_cannot_be_restarted():
    with pytest.raises(InvalidJobTransitionError):
        JobStateMachine.validate(JobStatus.COMPLETED, JobStatus.RUNNING)
    with pytest.raises(InvalidJobTransitionError):
        JobStateMachine.validate(JobStatus.CANCELLED, JobStatus.RUNNING)


def test_every_status_has_a_declared_transition_set():
    assert set(ALLOWED_TRANSITIONS) == set(JobStatus)
