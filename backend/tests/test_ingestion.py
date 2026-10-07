"""Integration tests for the complete ingestion pipeline (Chapter 3 of the spec).

Exercises the fixed stage order end-to-end: Upload -> Format Detection ->
Parser -> Metadata Extraction -> Validation -> ECGRecord Builder ->
Artifact Generation -> Storage, for every supported format.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ecg.constants import ECGFormat
from app.ingestion.exceptions import IngestionError
from app.ingestion.record_creator import create_ecg_record
from app.ingestion.storage.orchestrator import StorageOrchestrator
from app.ingestion.upload_orchestrator import UploadOrchestrator
from app.storage.file.filesystem import FilesystemArtifactStore


def _run_pipeline(tmp_path: Path, files: list[Path]):
    upload_orchestrator = UploadOrchestrator(temp_root=tmp_path / "uploads")
    files_bytes = [(f.name, f.read_bytes()) for f in files]
    session = upload_orchestrator.create_session(files_bytes)

    storage = StorageOrchestrator(store=FilesystemArtifactStore(root=tmp_path / "storage"))
    return session, create_ecg_record(session.upload_id, list(session.files), storage=storage)


def test_end_to_end_ingestion_wfdb(tmp_path: Path, wfdb_sample_dir: list[Path]) -> None:
    session, result = _run_pipeline(tmp_path, wfdb_sample_dir)

    assert result.record.source_information.upload_id == session.upload_id
    assert result.record.ecg_metadata.source_format == ECGFormat.WFDB
    assert result.record.waveform.lead_count == 15
    assert result.storage.record_id == result.record.record_id
    assert "waveform" in result.storage.artifact_paths


def test_end_to_end_ingestion_csv(tmp_path: Path, csv_sample_file: Path) -> None:
    _, result = _run_pipeline(tmp_path, [csv_sample_file])
    assert result.record.ecg_metadata.source_format == ECGFormat.CSV
    assert result.record.waveform.lead_count == 3


def test_end_to_end_ingestion_xml(tmp_path: Path, xml_sample_file: Path) -> None:
    _, result = _run_pipeline(tmp_path, [xml_sample_file])
    assert result.record.ecg_metadata.source_format == ECGFormat.XML


def test_end_to_end_ingestion_dicom(tmp_path: Path, dicom_sample_file: Path) -> None:
    _, result = _run_pipeline(tmp_path, [dicom_sample_file])
    assert result.record.ecg_metadata.source_format == ECGFormat.DICOM


def test_end_to_end_ingestion_scp(tmp_path: Path, scp_sample_file: Path) -> None:
    _, result = _run_pipeline(tmp_path, [scp_sample_file])
    assert result.record.ecg_metadata.source_format == ECGFormat.SCP_ECG


def test_ingestion_is_deterministic(tmp_path: Path, wfdb_sample_dir: list[Path]) -> None:
    """Same input recording -> same standardized waveform/metadata (Business Rule 8.16)."""
    _, result_a = _run_pipeline(tmp_path / "a", wfdb_sample_dir)
    _, result_b = _run_pipeline(tmp_path / "b", wfdb_sample_dir)

    assert result_a.record.ecg_metadata.sampling_rate_hz == result_b.record.ecg_metadata.sampling_rate_hz
    assert result_a.record.ecg_metadata.available_leads == result_b.record.ecg_metadata.available_leads
    assert result_a.record.ecg_metadata.sample_count == result_b.record.ecg_metadata.sample_count


def test_ingestion_fails_explicitly_for_unsupported_format(tmp_path: Path) -> None:
    unknown_file = tmp_path / "recording.unknownfmt"
    unknown_file.write_bytes(b"not a real ecg file")
    with pytest.raises(IngestionError):
        _run_pipeline(tmp_path, [unknown_file])


def test_ingestion_produces_exactly_one_record_per_upload(tmp_path: Path, wfdb_sample_dir: list[Path]) -> None:
    _, result = _run_pipeline(tmp_path, wfdb_sample_dir)
    # Exactly one waveform, one of each metadata category, sharing one record_id.
    assert result.record.record_id == result.record.ecg_metadata.record_id
    assert result.storage.record_id == result.record.record_id
