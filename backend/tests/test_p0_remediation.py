from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.ingestion.idempotency import effective_idempotency_key, request_fingerprint
from app.ingestion.upload_orchestrator import UploadOrchestrator
from app.reporting.constants import JobStatus, PipelineStage
from app.reporting.models.generation_job import ReportGenerationJob
from app.reporting.repositories.job_repository import ReportGenerationJobRepository
from app.storage import cloudinary_backup
from app.storage.file.filesystem import FilesystemArtifactStore


def test_ingest_fingerprint_is_stable_across_file_order() -> None:
    files_a = [("record.hea", b"header"), ("record.dat", b"signal")]
    files_b = list(reversed(files_a))
    assert request_fingerprint("pat-1", files_a) == request_fingerprint("pat-1", files_b)


def test_ingest_idempotency_is_scoped_to_tenant_and_requester() -> None:
    first = effective_idempotency_key(
        organisation_id="org-1", requested_by_user_id="user-1", fingerprint="abc", supplied_key=None
    )
    retry = effective_idempotency_key(
        organisation_id="org-1", requested_by_user_id="user-1", fingerprint="abc", supplied_key=None
    )
    other_tenant = effective_idempotency_key(
        organisation_id="org-2", requested_by_user_id="user-1", fingerprint="abc", supplied_key=None
    )
    assert first == retry
    assert first != other_tenant


def test_staged_upload_can_be_reopened_by_background_worker(tmp_path: Path) -> None:
    uploads = UploadOrchestrator(temp_root=tmp_path)
    created = uploads.create_session([("record.hea", b"header"), ("record.dat", b"signal")])
    reopened = uploads.get_session(created.upload_id)
    assert [path.name for path in reopened.files] == ["record.dat", "record.hea"]


def test_artifact_manifest_records_and_verifies_checksums(tmp_path: Path) -> None:
    store = FilesystemArtifactStore(root=tmp_path)
    store.write_bytes("rec-1", "waveform/waveform.npz", b"waveform")
    store.write_json("rec-1", "waveform/waveform_meta.json", {"samplingRateHz": 1000})
    manifest = store.finalize_artifact_manifest(
        "rec-1", ["waveform/waveform.npz", "waveform/waveform_meta.json"]
    )
    assert manifest["artifacts"][0]["checksumSha256"]
    store.verify_artifact_manifest("rec-1", manifest)

    store.write_bytes("rec-1", "waveform/waveform.npz", b"corrupt")
    with pytest.raises(Exception, match="checksum mismatch"):
        store.verify_artifact_manifest("rec-1", manifest)


def test_required_cloud_write_is_not_swallowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = FilesystemArtifactStore(root=tmp_path)
    store._durable_mode = "cloudinary"

    def fail_upload(*args, **kwargs):
        raise RuntimeError("object storage unavailable")

    monkeypatch.setattr(cloudinary_backup, "upload", fail_upload)
    with pytest.raises(Exception, match="Failed to durably store artifact"):
        store.write_bytes("rec-2", "waveform/waveform.npz", b"waveform")


def test_stale_running_report_job_becomes_terminal_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    session = Mock()
    job = ReportGenerationJob(
        id="rgj-stale",
        ecg_record_id="ecg-1",
        patient_id="pat-1",
        organisation_id="org-1",
        requested_by_user_id="user-1",
        status=JobStatus.RUNNING.value,
        current_stage=PipelineStage.LOAD_GENERATION_CONTEXT.value,
        progress_percent=0,
        attempt_count=1,
        stage_history=[],
        pipeline_version="test",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    repository = ReportGenerationJobRepository(session)
    assert repository.fail_if_stale(job) is True
    assert job.status == JobStatus.FAILED.value
    assert job.error_code == "REPORT_JOB_STALE"
    assert job.failed_stage == PipelineStage.LOAD_GENERATION_CONTEXT.value
    assert job.completed_at is not None
    session.commit.assert_called_once()
