"""Tests for the generated report artifact store (Sprint 4.2 / 9.10 / 9.11)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.reporting.exceptions import ReportArtifactStorageError, TransientReportingError
from app.reporting.storage import ReportArtifactStore


def test_a_written_artifact_reports_its_measured_size_and_checksum(tmp_path):
    store = ReportArtifactStore(root=tmp_path)
    data = b"<svg></svg>"

    stored = store.write(
        ecg_record_id="ecg-1", job_id="rgj-1", relative_path="visualizations/raw.svg", data=data
    )

    assert Path(stored.absolute_path).read_bytes() == data
    assert stored.file_size_bytes == len(data)
    assert stored.checksum_sha256 == hashlib.sha256(data).hexdigest()
    assert stored.relative_path == "visualizations/raw.svg"


def test_artifacts_are_scoped_by_recording_and_job(tmp_path):
    store = ReportArtifactStore(root=tmp_path)

    first = store.write(ecg_record_id="ecg-1", job_id="rgj-1", relative_path="a.svg", data=b"1")
    second = store.write(ecg_record_id="ecg-1", job_id="rgj-2", relative_path="a.svg", data=b"2")

    assert first.absolute_path != second.absolute_path
    assert store.job_dir("ecg-1", "rgj-1") == tmp_path / "ecg-1" / "rgj-1"
    assert Path(first.absolute_path).read_bytes() == b"1"
    assert Path(second.absolute_path).read_bytes() == b"2"


def test_nested_directories_are_created_on_demand(tmp_path):
    store = ReportArtifactStore(root=tmp_path)

    stored = store.write(
        ecg_record_id="ecg-1", job_id="rgj-1", relative_path="deep/nested/file.svg", data=b"x"
    )

    assert Path(stored.absolute_path).is_file()


def test_a_storage_failure_is_raised_and_is_retryable(tmp_path):
    """Storage failures are transient by classification (Sprint 2.13)."""
    blocker = tmp_path / "ecg-1"
    blocker.write_bytes(b"not a directory")
    store = ReportArtifactStore(root=tmp_path)

    with pytest.raises(ReportArtifactStorageError) as raised:
        store.write(ecg_record_id="ecg-1", job_id="rgj-1", relative_path="a.svg", data=b"x")

    assert isinstance(raised.value, TransientReportingError)
    assert raised.value.retryable
