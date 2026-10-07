"""Read-only access to the canonical ECG artifacts of a recording.

Sprint 3.6 lists the ECG Artifact Repository among the sources the Generation
Context Loader collects from. This repository is that source: it resolves the
artifacts ECG Ingestion wrote for a recording, reads the small JSON documents,
and describes the large binary artifacts by location and size.

Boundary (Sprint 3.23 / Module Responsibilities): reporting reads artifacts
and never parses, re-parses, preprocesses or modifies them. When the canonical
artifacts are missing, this repository fails loudly (Sprint 2.12 / 3.14
critical failure) rather than falling back to the original uploaded file --
turning a source file into a waveform is ECG Ingestion's responsibility.

The artifact layout mirrors the one written by
``app.ingestion.storage.orchestrator.StorageOrchestrator`` and the
preprocessing step of the ingest endpoint. It is expressed here as explicit
relative paths so a layout change surfaces as a single, obvious edit.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ingestion.exceptions import FileStorageError
from app.models import ECGRecord
from app.reporting.exceptions import ECGArtifactUnavailableError
from app.reporting.models.ecg_artifacts import ECGArtifactBundle, ECGArtifactRef
from app.storage.file.filesystem import FilesystemArtifactStore

WAVEFORM_ARTIFACT = "waveform/waveform.npz"
WAVEFORM_CSV_ARTIFACT = "waveform/waveform.csv"
WAVEFORM_DESCRIPTOR_ARTIFACT = "waveform/waveform_meta.json"
MANIFEST_ARTIFACT = "manifest/manifest.json"
PREPROCESSING_SIGNAL_ARTIFACT = "preprocessing/preprocessed.npz"
PREPROCESSING_REPORT_ARTIFACT = "preprocessing/preprocessing_report.json"

#: One JSON document per metadata category written by ingestion.
METADATA_CATEGORIES: tuple[str, ...] = (
    "patient_metadata",
    "ecg_metadata",
    "clinical_metadata",
    "device_metadata",
    "quality_metadata",
    "annotations",
    "source_information",
)


class ECGArtifactRepository:
    """Resolves and reads the stored artifacts of one ingested ECG recording."""

    def __init__(self, store: FilesystemArtifactStore | None = None) -> None:
        self._store = store or FilesystemArtifactStore()

    def load_bundle(self, record: ECGRecord) -> ECGArtifactBundle:
        """Collects every canonical artifact available for ``record``.

        The waveform artifact and its descriptor are mandatory; the metadata
        documents, manifest and preprocessing outputs are read when present
        and reported as absent otherwise.

        Raises:
            ECGArtifactUnavailableError: the recording was never ingested
                through the canonical pipeline, its artifact directory is
                missing, a mandatory artifact is absent, or a stored document
                cannot be read or parsed.
        """
        canonical_record_id = record.record_id
        if not canonical_record_id:
            raise ECGArtifactUnavailableError(
                f"ECG record {record.id!r} has no canonical record identifier: it was not ingested "
                "through the ECG ingestion pipeline and has no report-ready artifacts"
            )

        record_dir = self._store.record_dir(canonical_record_id)

        artifact_manifest = record.artifact_manifest
        if artifact_manifest is None:
            artifact_manifest = self._optional_document(
                record, canonical_record_id, "manifest/artifact_manifest.json"
            )
        if artifact_manifest is not None:
            try:
                self._store.verify_artifact_manifest(canonical_record_id, artifact_manifest)
            except FileStorageError as exc:
                raise ECGArtifactUnavailableError(
                    f"Canonical artifact verification failed for ECG record {record.id!r}: {exc}"
                ) from exc

        waveform = self._require_ref(record, canonical_record_id, WAVEFORM_ARTIFACT)
        waveform_descriptor = self._require_document(record, canonical_record_id, WAVEFORM_DESCRIPTOR_ARTIFACT)

        metadata_documents = {}
        for category in METADATA_CATEGORIES:
            document = self._optional_document(record, canonical_record_id, f"metadata/{category}.json")
            if document is not None:
                metadata_documents[category] = document

        return ECGArtifactBundle(
            record_dir=str(record_dir),
            waveform=waveform,
            waveform_descriptor=waveform_descriptor,
            metadata_documents=metadata_documents,
            waveform_csv=self._optional_ref(canonical_record_id, WAVEFORM_CSV_ARTIFACT),
            manifest=self._optional_document(record, canonical_record_id, MANIFEST_ARTIFACT),
            preprocessing_signal=self._optional_ref(canonical_record_id, PREPROCESSING_SIGNAL_ARTIFACT),
            preprocessing_report=self._optional_document(
                record, canonical_record_id, PREPROCESSING_REPORT_ARTIFACT
            ),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _path(self, canonical_record_id: str, relative_path: str) -> Path:
        return self._store.record_dir(canonical_record_id) / relative_path

    def _optional_ref(self, canonical_record_id: str, relative_path: str) -> ECGArtifactRef | None:
        try:
            path = self._store.materialize(canonical_record_id, relative_path)
        except FileStorageError:
            return None
        return ECGArtifactRef(
            relative_path=relative_path,
            absolute_path=str(path),
            size_bytes=path.stat().st_size,
        )

    def _require_ref(self, record: ECGRecord, canonical_record_id: str, relative_path: str) -> ECGArtifactRef:
        ref = self._optional_ref(canonical_record_id, relative_path)
        if ref is None:
            raise ECGArtifactUnavailableError(
                f"Required artifact {relative_path!r} is missing for ECG record {record.id!r} "
                f"(canonical {canonical_record_id!r})"
            )
        return ref

    def _optional_document(self, record: ECGRecord, canonical_record_id: str, relative_path: str) -> dict | None:
        """Reads a stored JSON document, or returns None when it was never written.

        A document that exists but cannot be read or parsed is an artifact
        integrity failure, not an absent section: it is raised rather than
        silently dropped, so a report is never generated from a partially
        readable recording.
        """
        try:
            return self._store.read_json(canonical_record_id, relative_path)
        except FileStorageError:
            return None
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ECGArtifactUnavailableError(
                f"Artifact {relative_path!r} for ECG record {record.id!r} "
                f"(canonical {canonical_record_id!r}) could not be read: {exc}"
            ) from exc

    def _require_document(self, record: ECGRecord, canonical_record_id: str, relative_path: str) -> dict:
        document = self._optional_document(record, canonical_record_id, relative_path)
        if document is None:
            raise ECGArtifactUnavailableError(
                f"Required artifact {relative_path!r} is missing for ECG record {record.id!r} "
                f"(canonical {canonical_record_id!r})"
            )
        return document
