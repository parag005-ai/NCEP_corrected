"""Unit tests for artifact generation and filesystem storage."""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from app.ingestion.builders.ecg_record_builder import ECGRecordBuilder
from app.ingestion.metadata_extractor import MetadataOrchestrator
from app.ingestion.parsers.wfdb.parser import WFDBParser
from app.ingestion.storage.orchestrator import StorageOrchestrator, StorageRequest
from app.ingestion.validator import ValidationOrchestrator
from app.storage.file.filesystem import FilesystemArtifactStore


def _build_record(wfdb_sample_dir: list[Path], record_id: str, upload_id: str):
    parsed = WFDBParser().parse(wfdb_sample_dir)
    metadata = MetadataOrchestrator.extract(parsed, record_id=record_id)
    validated = ValidationOrchestrator.validate(parsed, metadata)
    record = ECGRecordBuilder.build(validated, upload_id=upload_id)
    return record, validated


def test_storage_persists_all_artifacts(wfdb_sample_dir: list[Path], tmp_path: Path) -> None:
    record, validated = _build_record(wfdb_sample_dir, "rec-store-1", "upload-1")
    store = FilesystemArtifactStore(root=tmp_path / "storage_root")
    orchestrator = StorageOrchestrator(store=store)

    result = orchestrator.store(
        StorageRequest(
            record=record,
            upload_id="upload-1",
            source_files=tuple(wfdb_sample_dir),
            validation_result=validated.validation_result,
            processing_started_at=datetime.now(timezone.utc),
        )
    )

    assert store.exists("rec-store-1")
    for key in (
        "waveform",
        "patient_metadata",
        "ecg_metadata",
        "clinical_metadata",
        "device_metadata",
        "quality_metadata",
        "annotations",
        "source_information",
        "manifest",
    ):
        assert key in result.artifact_paths

    raw_files = list((store.record_dir("rec-store-1") / "raw").iterdir())
    assert {f.name for f in raw_files} == {"ptbsample.hea", "ptbsample.dat"}


def test_storage_waveform_artifact_round_trips_sample_values(wfdb_sample_dir: list[Path], tmp_path: Path) -> None:
    record, validated = _build_record(wfdb_sample_dir, "rec-store-2", "upload-2")
    store = FilesystemArtifactStore(root=tmp_path / "storage_root")
    orchestrator = StorageOrchestrator(store=store)

    orchestrator.store(
        StorageRequest(
            record=record,
            upload_id="upload-2",
            source_files=tuple(wfdb_sample_dir),
            validation_result=validated.validation_result,
            processing_started_at=datetime.now(timezone.utc),
        )
    )

    npz_bytes = store.read_bytes("rec-store-2", "waveform/waveform.npz")
    with np.load(io.BytesIO(npz_bytes)) as npz:
        for lead, signal in record.waveform.leads.items():
            assert np.array_equal(npz[lead.value], signal.samples)


def test_storage_manifest_reflects_validation_status(wfdb_sample_dir: list[Path], tmp_path: Path) -> None:
    record, validated = _build_record(wfdb_sample_dir, "rec-store-3", "upload-3")
    store = FilesystemArtifactStore(root=tmp_path / "storage_root")
    orchestrator = StorageOrchestrator(store=store)

    orchestrator.store(
        StorageRequest(
            record=record,
            upload_id="upload-3",
            source_files=tuple(wfdb_sample_dir),
            validation_result=validated.validation_result,
            processing_started_at=datetime.now(timezone.utc),
        )
    )

    manifest = store.read_json("rec-store-3", "manifest/manifest.json")
    assert manifest["validation_status"] == validated.validation_result.status.value
    assert manifest["record_id"] == "rec-store-3"
    assert manifest["upload_id"] == "upload-3"


def test_original_files_are_not_modified_by_storage(wfdb_sample_dir: list[Path], tmp_path: Path) -> None:
    record, validated = _build_record(wfdb_sample_dir, "rec-store-4", "upload-4")
    original_bytes = {f: f.read_bytes() for f in wfdb_sample_dir}
    store = FilesystemArtifactStore(root=tmp_path / "storage_root")
    orchestrator = StorageOrchestrator(store=store)

    orchestrator.store(
        StorageRequest(
            record=record,
            upload_id="upload-4",
            source_files=tuple(wfdb_sample_dir),
            validation_result=validated.validation_result,
            processing_started_at=datetime.now(timezone.utc),
        )
    )

    for f, content in original_bytes.items():
        assert f.read_bytes() == content


def test_raw_files_are_stored_read_only(wfdb_sample_dir: list[Path], tmp_path: Path) -> None:
    record, validated = _build_record(wfdb_sample_dir, "rec-store-readonly", "upload-readonly")
    store = FilesystemArtifactStore(root=tmp_path / "storage_root")
    orchestrator = StorageOrchestrator(store=store)

    orchestrator.store(
        StorageRequest(
            record=record,
            upload_id="upload-readonly",
            source_files=tuple(wfdb_sample_dir),
            validation_result=validated.validation_result,
            processing_started_at=datetime.now(timezone.utc),
        )
    )

    raw_dir = store.record_dir("rec-store-readonly") / "raw"
    for raw_file in raw_dir.iterdir():
        assert not os.access(raw_file, os.W_OK)


def test_storage_generates_standardized_waveform_csv(wfdb_sample_dir: list[Path], tmp_path: Path) -> None:
    record, validated = _build_record(wfdb_sample_dir, "rec-store-csv", "upload-csv")
    store = FilesystemArtifactStore(root=tmp_path / "storage_root")
    orchestrator = StorageOrchestrator(store=store)

    result = orchestrator.store(
        StorageRequest(
            record=record,
            upload_id="upload-csv",
            source_files=tuple(wfdb_sample_dir),
            validation_result=validated.validation_result,
            processing_started_at=datetime.now(timezone.utc),
        )
    )

    assert "waveform_csv" in result.artifact_paths
    csv_path = store.record_dir("rec-store-csv") / "waveform" / "waveform.csv"
    assert csv_path.exists()

    lines = csv_path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    assert header[:2] == ["sample_index", "time_s"]
    expected_leads = [lead.value for lead in record.waveform.available_leads]
    assert header[2:] == expected_leads
    # One header row plus exactly one row per sample -- no truncation, no padding.
    assert len(lines) - 1 == record.waveform.sample_count

    first_row = lines[1].split(",")
    assert int(first_row[0]) == 0
    assert float(first_row[1]) == pytest.approx(0.0)
    for col_idx, lead in enumerate(record.waveform.available_leads, start=2):
        expected_value = record.waveform.leads[lead].samples[0]
        assert float(first_row[col_idx]) == pytest.approx(expected_value, abs=1e-5)


def test_storage_rolls_back_all_artifacts_on_failure(
    wfdb_sample_dir: list[Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If any artifact write fails partway through, no partial record may remain on disk
    (Implementation Spec 15.8 -- atomic storage)."""
    from app.ingestion.storage import artifacts as artifacts_module

    record, validated = _build_record(wfdb_sample_dir, "rec-store-rollback", "upload-rollback")
    store = FilesystemArtifactStore(root=tmp_path / "storage_root")
    orchestrator = StorageOrchestrator(store=store)

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure while generating the processing manifest")

    monkeypatch.setattr(artifacts_module.ArtifactGenerator, "generate_manifest", staticmethod(_boom))

    with pytest.raises(RuntimeError):
        orchestrator.store(
            StorageRequest(
                record=record,
                upload_id="upload-rollback",
                source_files=tuple(wfdb_sample_dir),
                validation_result=validated.validation_result,
                processing_started_at=datetime.now(timezone.utc),
            )
        )

    assert not store.exists("rec-store-rollback")
    assert not store.record_dir("rec-store-rollback").exists()
