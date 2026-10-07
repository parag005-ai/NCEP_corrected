"""Storage Orchestrator (Storage Manager).

Purpose:
    Coordinate persistence of one ECGRecord: generate standardized output
    artifacts, preserve the original uploaded files, write everything
    under a record-scoped directory, and return a StorageResult
    (Implementation Spec Chapter 15).

Responsibilities:
    - Receive a completed ECGRecord and processing context.
    - Generate artifacts via ArtifactGenerator.
    - Persist original files, waveform, metadata, and manifest.
    - Report the storage outcome.

Shall NOT:
    - Parse ECG files.
    - Validate data.
    - Modify the ECGRecord.

Input:
    StorageRequest (ECGRecord, upload_id, original source files,
    ValidationResult, processing_started_at)

Output:
    StorageResult

Exceptions:
    FileStorageError -- raised (and propagated) when persistence fails;
    partial artifact writes are not treated as a successful storage
    outcome (Implementation Spec 15.8 -- atomic storage).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.ecg.models.ecg_record import ECGRecord
from app.ingestion.storage.artifacts import ArtifactGenerator, ProcessingManifest, metadata_to_dict
from app.ingestion.validation.validation_result import ValidationResult
from app.interfaces.storage import StorageInterface
from app.storage.file.filesystem import FilesystemArtifactStore


@dataclass(frozen=True)
class StorageRequest:
    """Input contract for the Storage Manager."""

    record: ECGRecord
    upload_id: str
    source_files: tuple[Path, ...]
    validation_result: ValidationResult
    processing_started_at: datetime


@dataclass(frozen=True)
class StorageResult:
    """Output of a successful storage operation."""

    record_id: str
    record_dir: str
    artifact_paths: dict[str, str] = field(default_factory=dict)
    manifest: ProcessingManifest | None = None


class StorageOrchestrator(StorageInterface):
    """Coordinates artifact generation and filesystem persistence for one ECGRecord."""

    def __init__(self, store: FilesystemArtifactStore | None = None) -> None:
        self._store = store or FilesystemArtifactStore()

    def store(self, payload: StorageRequest) -> StorageResult:
        """Persists every artifact for one ECGRecord, all-or-nothing.

        Storage is atomic at the record-directory granularity (Implementation
        Spec 15.8): if any artifact write fails partway through, every
        artifact already written for this record_id is rolled back so no
        partial record is ever left on disk.
        """
        record = payload.record
        record_id = record.record_id
        artifact_paths: dict[str, str] = {}

        try:
            for source_file in payload.source_files:
                self._store.copy_raw_file(record_id, source_file)

            waveform_bytes, waveform_descriptor = ArtifactGenerator.generate_waveform_artifact(record)
            artifact_paths["waveform"] = str(
                self._store.write_bytes(record_id, "waveform/waveform.npz", waveform_bytes)
            )
            self._store.write_json(record_id, "waveform/waveform_meta.json", waveform_descriptor)

            waveform_csv_bytes = ArtifactGenerator.generate_waveform_csv(record)
            artifact_paths["waveform_csv"] = str(
                self._store.write_bytes(record_id, "waveform/waveform.csv", waveform_csv_bytes)
            )

            for name, obj in (
                ("patient_metadata", record.patient_metadata),
                ("ecg_metadata", record.ecg_metadata),
                ("clinical_metadata", record.clinical_metadata),
                ("device_metadata", record.device_metadata),
                ("quality_metadata", record.quality_metadata),
                ("annotations", record.annotations),
                ("source_information", record.source_information),
            ):
                artifact_paths[name] = str(
                    self._store.write_json(record_id, f"metadata/{name}.json", metadata_to_dict(obj))
                )

            manifest = ArtifactGenerator.generate_manifest(
                record=record,
                validation_result=payload.validation_result,
                upload_id=payload.upload_id,
                started_at=payload.processing_started_at,
                completed_at=datetime.now(timezone.utc),
                generated_artifacts=tuple(artifact_paths.keys()),
            )
            artifact_paths["manifest"] = str(
                self._store.write_json(record_id, "manifest/manifest.json", metadata_to_dict(manifest))
            )
        except Exception:
            self._store.remove_record(record_id)
            raise

        return StorageResult(
            record_id=record_id,
            record_dir=str(self._store.record_dir(record_id)),
            artifact_paths=artifact_paths,
            manifest=manifest,
        )
