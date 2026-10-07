"""Unit tests for the reporting value objects and identifier generation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.reporting.constants import PipelineStage, StageStatus
from app.reporting.models import StageExecution, new_artifact_id, new_job_id, new_report_id


def test_stage_execution_duration_is_none_while_running():
    execution = StageExecution(
        stage=PipelineStage.LOAD_GENERATION_CONTEXT,
        status=StageStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )

    assert execution.duration_ms is None
    assert execution.to_dict()["duration_ms"] is None


def test_stage_execution_duration_is_derived_from_timestamps():
    started_at = datetime.now(timezone.utc)
    execution = StageExecution(
        stage=PipelineStage.GENERATE_VISUALIZATIONS,
        status=StageStatus.COMPLETED,
        started_at=started_at,
        completed_at=started_at + timedelta(milliseconds=1500),
    )

    assert execution.duration_ms == 1500


def test_stage_execution_survives_a_serialization_round_trip():
    started_at = datetime.now(timezone.utc)
    execution = StageExecution(
        stage=PipelineStage.RENDER_HTML_DOCUMENTS,
        status=StageStatus.PARTIAL_SUCCESS,
        started_at=started_at,
        completed_at=started_at + timedelta(seconds=2),
        attempt=2,
        error_code="TEMPLATE_SECTION_UNAVAILABLE",
        error_message="Signal processing section rendered as placeholder",
        artifact_ids=("rart-abc", "rart-def"),
        messages=("summary rendered", "detailed rendered"),
    )

    restored = StageExecution.from_dict(execution.to_dict())

    assert restored == execution


def test_stage_execution_accepts_a_minimal_persisted_record():
    """History written by an earlier pipeline version must still load."""
    restored = StageExecution.from_dict(
        {
            "stage": PipelineStage.STORE_REPORT_ARTIFACTS.value,
            "status": StageStatus.SKIPPED.value,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    assert restored.completed_at is None
    assert restored.attempt == 1
    assert restored.artifact_ids == ()
    assert restored.messages == ()


def test_identifiers_are_prefixed_and_unique():
    assert new_job_id().startswith("rgj-")
    assert new_report_id().startswith("grp-")
    assert new_artifact_id().startswith("rart-")
    assert len({new_job_id() for _ in range(100)}) == 100
