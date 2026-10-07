"""Persistence tests for the reporting repository layer (Sprint 2.18)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.reporting.constants import (
    REPORT_PIPELINE_VERSION,
    REPORT_SCHEMA_VERSION,
    REPORTING_SOFTWARE_VERSION,
    ArtifactStatus,
    ArtifactType,
    JobStatus,
    PipelineStage,
    ReportStatus,
    StageStatus,
)
from app.reporting.exceptions import (
    GeneratedReportNotFoundError,
    ReportArtifactNotFoundError,
    ReportJobNotFoundError,
)
from app.reporting.models import GeneratedReport, JobFailure, ReportGenerationJob, StageExecution
from app.reporting.repositories import (
    GeneratedReportRepository,
    ReportArtifactRepository,
    ReportGenerationJobRepository,
)

from tests.reporting.conftest import UpstreamFixture

SUMMARY_TEMPLATE = ("ncep-summary", "1.0.0")
DETAILED_TEMPLATE = ("ncep-detailed", "1.0.0")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_job(
    session: Session, upstream: UpstreamFixture, *, ecg_record_id: str | None = None
) -> ReportGenerationJob:
    return ReportGenerationJobRepository(session).create(
        ecg_record_id=ecg_record_id or upstream.ecg_record_id,
        patient_id=upstream.patient_id,
        organisation_id=upstream.organisation_id,
        requested_by_user_id=upstream.user_id,
        requested_by_doctor_id=upstream.doctor_id,
    )


def make_report(
    session: Session,
    upstream: UpstreamFixture,
    *,
    job: ReportGenerationJob | None = None,
    version: int | None = None,
) -> GeneratedReport:
    reports = GeneratedReportRepository(session)
    job = job or make_job(session, upstream)
    version = version if version is not None else reports.next_version(job.ecg_record_id)
    return reports.create(
        job=job,
        version=version,
        doctor_id=upstream.doctor_id,
        storage_dir=f"reports/{job.ecg_record_id}/v{version}",
        summary_template_id=SUMMARY_TEMPLATE[0],
        summary_template_version=SUMMARY_TEMPLATE[1],
        detailed_template_id=DETAILED_TEMPLATE[0],
        detailed_template_version=DETAILED_TEMPLATE[1],
    )


# ---------------------------------------------------------------------------
# ReportGenerationJobRepository
# ---------------------------------------------------------------------------


def test_created_job_starts_in_requested_state_with_empty_history(session, upstream):
    job = make_job(session, upstream)

    assert job.id.startswith("rgj-")
    assert job.status == JobStatus.REQUESTED.value
    assert job.current_stage is None
    assert job.progress_percent == 0
    assert job.attempt_count == 0
    assert job.stage_history == []
    assert job.pipeline_version == REPORT_PIPELINE_VERSION
    assert job.started_at is None and job.completed_at is None
    assert job.created_at is not None and job.updated_at is not None


def test_job_lineage_must_reference_an_existing_ecg_record(session, upstream):
    repository = ReportGenerationJobRepository(session)

    with pytest.raises(IntegrityError):
        repository.create(
            ecg_record_id="ecg-does-not-exist",
            patient_id=upstream.patient_id,
            organisation_id=upstream.organisation_id,
            requested_by_user_id=upstream.user_id,
        )


def test_require_raises_for_an_unknown_job(session):
    with pytest.raises(ReportJobNotFoundError):
        ReportGenerationJobRepository(session).require("rgj-missing")

    assert ReportGenerationJobRepository(session).get("rgj-missing") is None


def test_update_execution_state_writes_only_supplied_fields(session, upstream):
    repository = ReportGenerationJobRepository(session)
    job = make_job(session, upstream)
    created_updated_at = job.updated_at
    started_at = datetime.now(timezone.utc)

    repository.update_execution_state(
        job,
        status=JobStatus.RUNNING,
        current_stage=PipelineStage.LOAD_GENERATION_CONTEXT,
        progress_percent=10,
        started_at=started_at,
    )

    assert job.status == JobStatus.RUNNING.value
    assert job.current_stage == PipelineStage.LOAD_GENERATION_CONTEXT.value
    assert job.progress_percent == 10
    assert job.started_at == started_at
    assert job.completed_at is None
    assert job.updated_at >= created_updated_at

    repository.update_execution_state(job, progress_percent=40)

    assert job.progress_percent == 40
    assert job.status == JobStatus.RUNNING.value
    assert job.current_stage == PipelineStage.LOAD_GENERATION_CONTEXT.value


def test_update_execution_state_records_failure_details(session, upstream):
    repository = ReportGenerationJobRepository(session)
    job = make_job(session, upstream)

    repository.update_execution_state(
        job,
        status=JobStatus.FAILED,
        completed_at=datetime.now(timezone.utc),
        failure=JobFailure(
            code="ECG_ARTIFACT_UNAVAILABLE",
            message="Waveform artifact could not be read",
            stage=PipelineStage.LOAD_GENERATION_CONTEXT,
        ),
    )

    assert job.status == JobStatus.FAILED.value
    assert job.failed_stage == PipelineStage.LOAD_GENERATION_CONTEXT.value
    assert job.error_code == "ECG_ARTIFACT_UNAVAILABLE"
    assert job.error_message == "Waveform artifact could not be read"
    assert job.completed_at is not None


def test_stage_history_accumulates_and_survives_a_reload(session, upstream):
    repository = ReportGenerationJobRepository(session)
    job = make_job(session, upstream)
    started_at = datetime.now(timezone.utc)

    first = StageExecution(
        stage=PipelineStage.LOAD_GENERATION_CONTEXT,
        status=StageStatus.COMPLETED,
        started_at=started_at,
        completed_at=started_at + timedelta(milliseconds=250),
    )
    second = StageExecution(
        stage=PipelineStage.EVALUATE_CLINICAL_RULES,
        status=StageStatus.SKIPPED,
        started_at=started_at + timedelta(seconds=1),
        messages=("signal processing outputs unavailable",),
    )
    repository.append_stage_execution(job, first)
    repository.append_stage_execution(job, second)
    session.commit()
    session.expire_all()

    reloaded = repository.require(job.id)
    history = [StageExecution.from_dict(entry) for entry in reloaded.stage_history]

    assert history == [first, second]


def test_increment_attempt_counts_orchestrator_retries(session, upstream):
    repository = ReportGenerationJobRepository(session)
    job = make_job(session, upstream)

    repository.increment_attempt(job)
    repository.increment_attempt(job)

    assert job.attempt_count == 2


def test_job_history_is_scoped_to_one_recording(session, upstream):
    repository = ReportGenerationJobRepository(session)
    make_job(session, upstream)
    make_job(session, upstream)
    other = make_job(session, upstream, ecg_record_id=upstream.other_ecg_record_id)
    session.commit()

    listed = repository.list_for_ecg_record(upstream.ecg_record_id)

    assert len(listed) == 2
    assert other.id not in {job.id for job in listed}
    assert listed[0].created_at >= listed[1].created_at


# ---------------------------------------------------------------------------
# GeneratedReportRepository
# ---------------------------------------------------------------------------


def test_report_versions_are_sequential_per_recording(session, upstream):
    repository = GeneratedReportRepository(session)

    assert repository.next_version(upstream.ecg_record_id) == 1

    make_report(session, upstream)
    session.commit()

    assert repository.next_version(upstream.ecg_record_id) == 2
    assert repository.next_version(upstream.other_ecg_record_id) == 1


def test_created_report_takes_its_lineage_from_the_job(session, upstream):
    job = make_job(session, upstream)

    report = make_report(session, upstream, job=job)

    assert report.id.startswith("grp-")
    assert report.job_id == job.id
    assert report.ecg_record_id == job.ecg_record_id
    assert report.patient_id == job.patient_id
    assert report.organisation_id == job.organisation_id
    assert report.version == 1
    assert report.status == ReportStatus.GENERATING.value
    assert report.summary_template_id == SUMMARY_TEMPLATE[0]
    assert report.detailed_template_version == DETAILED_TEMPLATE[1]
    assert report.pipeline_version == REPORT_PIPELINE_VERSION
    assert report.schema_version == REPORT_SCHEMA_VERSION
    assert report.software_version == REPORTING_SOFTWARE_VERSION
    assert report.rules_version is None
    assert report.narrative_model_version is None
    assert report.generated_at is not None


def test_a_recording_cannot_have_two_reports_with_the_same_version(session, upstream):
    make_report(session, upstream, version=1)

    with pytest.raises(IntegrityError):
        make_report(session, upstream, version=1)


def test_a_job_produces_at_most_one_report(session, upstream):
    job = make_job(session, upstream)
    make_report(session, upstream, job=job, version=1)

    with pytest.raises(IntegrityError):
        make_report(session, upstream, job=job, version=2)


def test_reports_are_retrievable_by_job_version_and_latest(session, upstream):
    repository = GeneratedReportRepository(session)
    first = make_report(session, upstream, version=1)
    second = make_report(session, upstream, version=2)
    session.commit()

    assert repository.get_by_job(first.job_id).id == first.id
    assert repository.get_version(upstream.ecg_record_id, 1).id == first.id
    assert repository.get_latest_for_ecg_record(upstream.ecg_record_id).id == second.id
    assert repository.get_latest_for_ecg_record(upstream.other_ecg_record_id) is None
    assert repository.require(first.id).id == first.id


def test_report_history_is_newest_version_first(session, upstream):
    repository = GeneratedReportRepository(session)
    make_report(session, upstream, version=1)
    make_report(session, upstream, version=2)
    make_report(session, upstream, version=3)
    session.commit()

    history = repository.list_for_ecg_record(upstream.ecg_record_id)

    assert [report.version for report in history] == [3, 2, 1]


def test_require_raises_for_an_unknown_report(session):
    with pytest.raises(GeneratedReportNotFoundError):
        GeneratedReportRepository(session).require("grp-missing")


def test_report_status_advances_without_touching_report_content(session, upstream):
    repository = GeneratedReportRepository(session)
    report = make_report(session, upstream)
    original_generated_at = report.generated_at

    repository.update_status(report, ReportStatus.AVAILABLE)

    assert report.status == ReportStatus.AVAILABLE.value
    assert report.generated_at == original_generated_at
    assert report.version == 1


# ---------------------------------------------------------------------------
# ReportArtifactRepository
# ---------------------------------------------------------------------------


def register_artifact(
    session: Session,
    report: GeneratedReport,
    *,
    artifact_type: ArtifactType = ArtifactType.SUMMARY_HTML,
    storage_location: str = "summary.html",
):
    return ReportArtifactRepository(session).register(
        report=report,
        artifact_type=artifact_type,
        content_type="text/html; charset=utf-8",
        storage_location=storage_location,
        file_size_bytes=2048,
        checksum_sha256="a" * 64,
    )


def test_registered_artifact_carries_its_report_and_recording(session, upstream):
    report = make_report(session, upstream)

    artifact = register_artifact(session, report)

    assert artifact.id.startswith("rart-")
    assert artifact.report_id == report.id
    assert artifact.ecg_record_id == report.ecg_record_id
    assert artifact.artifact_type == ArtifactType.SUMMARY_HTML.value
    assert artifact.status == ArtifactStatus.REGISTERED.value
    assert artifact.checksum_sha256 == "a" * 64
    assert artifact.file_size_bytes == 2048
    assert artifact.generated_at is not None


def test_one_storage_location_can_only_be_registered_once_per_report(session, upstream):
    report = make_report(session, upstream)
    register_artifact(session, report, storage_location="summary.html")

    with pytest.raises(IntegrityError):
        register_artifact(session, report, storage_location="summary.html")


def test_artifacts_are_listed_per_report_and_filterable_by_type(session, upstream):
    report = make_report(session, upstream)
    other_report = make_report(session, upstream, version=2)
    register_artifact(session, report, artifact_type=ArtifactType.SUMMARY_HTML, storage_location="summary.html")
    register_artifact(session, report, artifact_type=ArtifactType.DETAILED_HTML, storage_location="detailed.html")
    register_artifact(session, other_report, artifact_type=ArtifactType.SUMMARY_HTML, storage_location="summary.html")
    session.commit()

    repository = ReportArtifactRepository(session)
    all_artifacts = repository.list_for_report(report.id)
    summary_only = repository.list_for_report(report.id, artifact_type=ArtifactType.SUMMARY_HTML)

    assert len(all_artifacts) == 2
    assert [artifact.artifact_type for artifact in summary_only] == [ArtifactType.SUMMARY_HTML.value]


def test_artifact_specific_metadata_is_preserved(session, upstream):
    """A visualization records its type, lead and time window (Sprint 4.12)."""
    report = make_report(session, upstream)

    artifact = ReportArtifactRepository(session).register(
        report=report,
        artifact_type=ArtifactType.RAW_ECG_SVG,
        content_type="image/svg+xml",
        storage_location="visualizations/raw_ecg_lead_II.svg",
        file_size_bytes=4096,
        checksum_sha256="b" * 64,
        artifact_metadata={
            "visualization_type": "RAW_ECG",
            "lead": "II",
            "window_start_second": 0.0,
            "window_end_second": 10.0,
        },
    )
    session.commit()
    session.expire_all()

    reloaded = ReportArtifactRepository(session).require(artifact.id)
    assert reloaded.artifact_metadata["lead"] == "II"
    assert reloaded.artifact_metadata["window_end_second"] == 10.0


def test_artifacts_without_specific_metadata_store_none(session, upstream):
    report = make_report(session, upstream)

    artifact = register_artifact(session, report)

    assert artifact.artifact_metadata is None


def test_artifact_status_advances_along_its_lifecycle(session, upstream):
    report = make_report(session, upstream)
    artifact = register_artifact(session, report)

    ReportArtifactRepository(session).update_status(artifact, ArtifactStatus.AVAILABLE)

    assert artifact.status == ArtifactStatus.AVAILABLE.value


def test_require_raises_for_an_unknown_artifact(session):
    with pytest.raises(ReportArtifactNotFoundError):
        ReportArtifactRepository(session).require("rart-missing")


def test_deleting_a_report_removes_its_registered_artifacts(session, upstream):
    report = make_report(session, upstream)
    artifact_id = register_artifact(session, report).id
    session.commit()

    session.delete(report)
    session.commit()
    session.expunge_all()

    assert ReportArtifactRepository(session).get(artifact_id) is None
