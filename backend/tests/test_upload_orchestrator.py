"""Unit tests for the Upload Layer: UploadOrchestrator and UploadStatusStore."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion.exceptions import DuplicateFilenameError, UploadTooLargeError
from app.ingestion.upload_orchestrator import UploadOrchestrator
from app.ingestion.upload_status import UploadStatus, UploadStatusStore


# -- Duplicate filenames -------------------------------------------------------------


def test_create_session_rejects_duplicate_filenames(tmp_path: Path) -> None:
    orchestrator = UploadOrchestrator(temp_root=tmp_path / "uploads")
    with pytest.raises(DuplicateFilenameError):
        orchestrator.create_session([("sample.dat", b"aaa"), ("sample.dat", b"bbb")])


def test_create_session_allows_distinct_filenames(tmp_path: Path) -> None:
    orchestrator = UploadOrchestrator(temp_root=tmp_path / "uploads")
    session = orchestrator.create_session([("a.hea", b"aaa"), ("a.dat", b"bbb")])
    assert {f.name for f in session.files} == {"a.hea", "a.dat"}


# -- Upload size limits -------------------------------------------------------------


def test_create_session_rejects_oversized_upload(tmp_path: Path) -> None:
    orchestrator = UploadOrchestrator(temp_root=tmp_path / "uploads", max_upload_size_bytes=10)
    with pytest.raises(UploadTooLargeError):
        orchestrator.create_session([("big.csv", b"x" * 100)])


def test_create_session_allows_upload_within_limit(tmp_path: Path) -> None:
    orchestrator = UploadOrchestrator(temp_root=tmp_path / "uploads", max_upload_size_bytes=1000)
    session = orchestrator.create_session([("small.csv", b"x" * 10)])
    assert session.files


# -- Temporary file cleanup -------------------------------------------------------------


def test_cleanup_session_removes_temp_directory(tmp_path: Path) -> None:
    orchestrator = UploadOrchestrator(temp_root=tmp_path / "uploads")
    session = orchestrator.create_session([("a.csv", b"data")])
    assert session.session_dir.exists()

    orchestrator.cleanup_session(session)

    assert not session.session_dir.exists()


def test_cleanup_session_is_idempotent(tmp_path: Path) -> None:
    orchestrator = UploadOrchestrator(temp_root=tmp_path / "uploads")
    session = orchestrator.create_session([("a.csv", b"data")])
    orchestrator.cleanup_session(session)
    orchestrator.cleanup_session(session)  # must not raise


# -- Upload status persistence -------------------------------------------------------------


def test_upload_status_store_persists_across_new_instances(tmp_path: Path) -> None:
    """A brand-new UploadStatusStore instance reading the same directory must see prior
    status -- this is what makes upload status survive an application restart."""
    status_dir = tmp_path / "status"
    store_a = UploadStatusStore(root=status_dir)
    store_a.set(UploadStatus(upload_id="up-1", state="COMPLETED", record_id="rec-1"))

    store_b = UploadStatusStore(root=status_dir)
    status = store_b.get("up-1")

    assert status is not None
    assert status.state == "COMPLETED"
    assert status.record_id == "rec-1"
    assert status.detail is None


def test_upload_status_store_returns_none_for_unknown_upload(tmp_path: Path) -> None:
    store = UploadStatusStore(root=tmp_path / "status")
    assert store.get("does-not-exist") is None


def test_upload_status_store_records_failure_detail(tmp_path: Path) -> None:
    store = UploadStatusStore(root=tmp_path / "status")
    store.set(UploadStatus(upload_id="up-2", state="FAILED", detail="validation failed"))

    status = store.get("up-2")
    assert status.state == "FAILED"
    assert status.record_id is None
    assert status.detail == "validation failed"
