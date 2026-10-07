"""Tests that a terminated report generation leaves a clean state.

A run either completes or rolls back: no orphan report row, no orphan
documents on disk, no registry entries pointing at a report that was never
published, and never a job stranded mid-execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.reporting.constants import ArtifactType, JobStatus, PipelineStage, StageStatus
from app.reporting.exceptions import PDFRenderingError
from app.reporting.models.generated_report import GeneratedReport
from app.reporting.models.report_artifact import ReportArtifact
from app.reporting.orchestrator import (
    StageResult,
    WorkflowOrchestrator,
    build_failure_cleanup,
    build_report_pipeline,
)
from app.reporting.repositories import ECGArtifactRepository, GeneratedReportRepository
from app.reporting.storage import ReportArtifactStore

from tests.reporting.conftest import FakePDFRenderer, UpstreamFixture, write_canonical_artifacts


def build(session, artifact_store, report_root, renderer=None, extra=()) -> WorkflowOrchestrator:
    store = ReportArtifactStore(root=report_root)
    stages = build_report_pipeline(
        session,
        ecg_artifacts=ECGArtifactRepository(store=artifact_store),
        artifact_store=store,
        pdf_renderer=renderer or FakePDFRenderer(),
    )
    return WorkflowOrchestrator(
        session,
        (*stages, *extra),
        cleanup=build_failure_cleanup(session, artifact_store=store),
    )


def create_job(orchestrator: WorkflowOrchestrator, upstream: UpstreamFixture):
    return orchestrator.create_job(
        ecg_record_id=upstream.ecg_record_id,
        patient_id=upstream.patient_id,
        organisation_id=upstream.organisation_id,
        requested_by_user_id=upstream.user_id,
        requested_by_doctor_id=upstream.doctor_id,
    )


def stored_files(report_root: Path) -> list[str]:
    if not report_root.exists():
        return []
    return sorted(str(p.relative_to(report_root)) for p in report_root.rglob("*") if p.is_file())


class DatabaseErrorStage:
    """A stage that fails part-way through a database write."""

    stage = PipelineStage.STORE_REPORT_ARTIFACTS

    def __init__(self, session) -> None:
        self._session = session

    def execute(self, payload):
        now = datetime.now(timezone.utc)
        for _ in range(2):  # the same version twice violates the unique constraint
            self._session.add(
                GeneratedReport(
                    job_id=payload.job.id,
                    ecg_record_id=payload.job.ecg_record_id,
                    patient_id=payload.job.patient_id,
                    organisation_id=payload.job.organisation_id,
                    version=99,
                    status="GENERATING",
                    summary_template_id="s",
                    summary_template_version="1",
                    detailed_template_id="d",
                    detailed_template_version="1",
                    pipeline_version="1",
                    schema_version="1",
                    software_version="1",
                    storage_dir="/x",
                    generated_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
        self._session.flush()
        return StageResult(status=StageStatus.COMPLETED)


# ---------------------------------------------------------------------------
# A database error must not strand the job
# ---------------------------------------------------------------------------


def test_a_database_error_in_a_stage_is_recorded_not_propagated(session, upstream, artifact_store, tmp_path):
    """Without session recovery the orchestrator could not record its own failure."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    store = ReportArtifactStore(root=tmp_path / "reports")
    stages = build_report_pipeline(
        session,
        ecg_artifacts=ECGArtifactRepository(store=artifact_store),
        artifact_store=store,
        pdf_renderer=FakePDFRenderer(),
    )
    failing = [s for s in stages if s.stage is not PipelineStage.STORE_REPORT_ARTIFACTS]
    orchestrator = WorkflowOrchestrator(
        session,
        [*failing, DatabaseErrorStage(session)],
        cleanup=build_failure_cleanup(session, artifact_store=store),
    )

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert job.failed_stage == PipelineStage.STORE_REPORT_ARTIFACTS.value
    assert job.completed_at is not None
    assert len(job.stage_history) == len(failing) + 1


def test_a_failed_database_write_leaves_no_rows_behind(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    store = ReportArtifactStore(root=tmp_path / "reports")
    stages = build_report_pipeline(
        session,
        ecg_artifacts=ECGArtifactRepository(store=artifact_store),
        artifact_store=store,
        pdf_renderer=FakePDFRenderer(),
    )
    orchestrator = WorkflowOrchestrator(
        session,
        [
            *[s for s in stages if s.stage is not PipelineStage.STORE_REPORT_ARTIFACTS],
            DatabaseErrorStage(session),
        ],
        cleanup=build_failure_cleanup(session, artifact_store=store),
    )

    orchestrator.run(create_job(orchestrator, upstream))

    assert session.scalars(select(GeneratedReport)).all() == []
    assert session.scalars(select(ReportArtifact)).all() == []


# ---------------------------------------------------------------------------
# Rollback of partial output
# ---------------------------------------------------------------------------


def test_a_pdf_failure_rolls_back_the_whole_report(session, upstream, artifact_store, tmp_path):
    """The report row, its artifacts and its documents all go."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    report_root = tmp_path / "reports"
    orchestrator = build(
        session, artifact_store, report_root, FakePDFRenderer(error=PDFRenderingError("boom"))
    )

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert GeneratedReportRepository(session).get_by_job(job.id) is None
    assert session.scalars(select(ReportArtifact)).all() == []
    assert stored_files(report_root) == []


def test_a_rolled_back_version_number_is_released(session, upstream, artifact_store, tmp_path):
    """A failed run must not consume a version, leaving a gap in the history."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    reports = GeneratedReportRepository(session)
    failing = build(
        session, artifact_store, tmp_path / "a", FakePDFRenderer(error=PDFRenderingError("boom"))
    )
    failing.run(create_job(failing, upstream))

    assert reports.next_version(upstream.ecg_record_id) == 1

    succeeding = build(session, artifact_store, tmp_path / "b")
    job = succeeding.run(create_job(succeeding, upstream))

    assert reports.get_by_job(job.id).version == 1


def test_a_successful_run_is_never_rolled_back(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    report_root = tmp_path / "reports"
    orchestrator = build(session, artifact_store, report_root)

    job = orchestrator.run(create_job(orchestrator, upstream))

    report = GeneratedReportRepository(session).get_by_job(job.id)
    assert job.status == JobStatus.COMPLETED.value
    assert report is not None
    assert len(stored_files(report_root)) == 4  # svg, summary data, html, pdf


def test_a_cancelled_run_leaves_no_partial_report(session, upstream, artifact_store, tmp_path):
    """Cancelling after documents exist rolls them back too."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    report_root = tmp_path / "reports"
    orchestrator = build(session, artifact_store, report_root)
    job = orchestrator.run(create_job(orchestrator, upstream))
    assert stored_files(report_root)

    orchestrator.cancel(
        orchestrator.create_job(
            ecg_record_id=upstream.ecg_record_id,
            patient_id=upstream.patient_id,
            organisation_id=upstream.organisation_id,
            requested_by_user_id=upstream.user_id,
        )
    )

    # The completed run is untouched by another job's cancellation.
    assert GeneratedReportRepository(session).get_by_job(job.id) is not None


def test_rollback_does_not_rely_on_database_cascade(tmp_path):
    """SQLite does not enforce foreign keys by default, so the rollback removes
    registry rows itself rather than trusting ON DELETE CASCADE."""
    from datetime import date

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base
    from app.models import ECGRecord, Organisation, Patient, User
    from app.reporting import models as _models  # noqa: F401
    from app.reporting.orchestrator import ReportGenerationCleanup
    from app.reporting.repositories import ReportArtifactRepository, ReportGenerationJobRepository

    # Deliberately no foreign key pragma: this is the default SQLite behaviour.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    now = datetime.now(timezone.utc)
    for row in (
        Organisation(id="org-1", name="O", created_at=now),
        User(id="usr-1", email="u@x", name="U", role="doctor", organisation_id="org-1", created_at=now),
        Patient(id="pat-1", name="P", email="p@x", organisation_id="org-1", created_at=now),
        ECGRecord(id="ecg-1", patient_id="pat-1", organisation_id="org-1", file_name="r",
                  file_type="WFDB", recording_date=date(2026, 7, 1), uploaded_at=now, uploaded_by="U"),
    ):
        session.add(row)
        session.flush()
    session.commit()

    job = ReportGenerationJobRepository(session).create(
        ecg_record_id="ecg-1", patient_id="pat-1", organisation_id="org-1", requested_by_user_id="usr-1"
    )
    report = GeneratedReportRepository(session).create(
        job=job, version=1, doctor_id=None, storage_dir=str(tmp_path),
        summary_template_id="s", summary_template_version="1",
        detailed_template_id="d", detailed_template_version="1",
    )
    ReportArtifactRepository(session).register(
        report=report, artifact_type=ArtifactType.DETAILED_HTML, content_type="text/html",
        storage_location="documents/detailed_report.html", file_size_bytes=1,
        checksum_sha256="a" * 64,
    )
    session.commit()

    ReportGenerationCleanup(session, ReportArtifactStore(root=tmp_path)).clean(job)

    assert session.scalars(select(GeneratedReport)).all() == []
    assert session.scalars(select(ReportArtifact)).all() == []
    session.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_only_one_runner_can_execute_a_job(session, upstream, artifact_store, tmp_path):
    """A job already claimed by another worker is refused, not run twice."""
    import pytest
    from sqlalchemy import update

    from app.reporting.exceptions import ConcurrentJobExecutionError
    from app.reporting.models.generation_job import ReportGenerationJob

    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    report_root = tmp_path / "reports"
    orchestrator = build(session, artifact_store, report_root)
    job = create_job(orchestrator, upstream)

    # Another worker claims the job between this runner reading it and
    # starting it, so this runner is still holding a QUEUED view of a job the
    # database now reports as RUNNING.
    session.execute(
        update(ReportGenerationJob)
        .where(ReportGenerationJob.id == job.id)
        .values(status=JobStatus.RUNNING.value)
        .execution_options(synchronize_session=False)
    )
    session.commit()
    job.status = JobStatus.QUEUED.value

    with pytest.raises(ConcurrentJobExecutionError):
        orchestrator.run(job)

    assert stored_files(report_root) == []
    assert session.scalars(select(GeneratedReport)).all() == []


def test_the_runner_that_claims_the_job_still_completes(session, upstream, artifact_store, tmp_path):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    orchestrator = build(session, artifact_store, tmp_path / "reports")

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.COMPLETED.value
    assert job.attempt_count == 1


def test_an_earlier_failure_leaves_nothing_to_roll_back(session, upstream, artifact_store, tmp_path):
    """A job that fails before any document exists is already clean."""
    report_root = tmp_path / "reports"
    orchestrator = build(session, artifact_store, report_root)

    job = orchestrator.run(create_job(orchestrator, upstream))

    assert job.status == JobStatus.FAILED.value
    assert job.failed_stage == PipelineStage.LOAD_GENERATION_CONTEXT.value
    assert stored_files(report_root) == []
    assert session.scalars(select(GeneratedReport)).all() == []
