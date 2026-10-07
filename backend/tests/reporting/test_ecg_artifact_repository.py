"""Tests for read-only access to the canonical ECG artifacts of a recording."""

from __future__ import annotations

import pytest

from app.models import ECGRecord
from app.reporting.exceptions import ECGArtifactUnavailableError
from app.reporting.repositories import ECGArtifactRepository
from app.reporting.repositories.ecg_artifact_repository import (
    METADATA_CATEGORIES,
    WAVEFORM_ARTIFACT,
    WAVEFORM_DESCRIPTOR_ARTIFACT,
)

from tests.reporting.conftest import write_canonical_artifacts


def test_bundle_collects_every_stored_artifact(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    record = session.get(ECGRecord, upstream.ecg_record_id)

    bundle = ECGArtifactRepository(store=artifact_store).load_bundle(record)

    assert bundle.record_dir == str(artifact_store.record_dir(upstream.canonical_record_id))
    assert bundle.waveform.relative_path == WAVEFORM_ARTIFACT
    assert bundle.waveform.size_bytes > 0
    assert bundle.waveform.absolute_path.endswith("waveform.npz")
    assert bundle.waveform_descriptor["sampling_rate_hz"] == 1000.0
    assert set(bundle.metadata_documents) == set(METADATA_CATEGORIES)
    assert bundle.waveform_csv is not None
    assert bundle.manifest["record_id"] == upstream.canonical_record_id
    assert bundle.preprocessing_signal is not None
    assert bundle.preprocessing_report["beat_count"] == 12


def test_bundle_reports_absent_optional_artifacts_without_failing(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id, include_optional=False)
    record = session.get(ECGRecord, upstream.ecg_record_id)

    bundle = ECGArtifactRepository(store=artifact_store).load_bundle(record)

    assert bundle.waveform_csv is None
    assert bundle.manifest is None
    assert bundle.preprocessing_signal is None
    assert bundle.preprocessing_report is None
    assert bundle.metadata_documents == {}


def test_a_recording_without_canonical_artifacts_cannot_be_reported_on(session, upstream, artifact_store):
    """A recording that never went through ingestion has no report-ready artifacts.

    Reporting must not fall back to re-parsing the original uploaded file:
    parsing belongs to ECG Ingestion (module boundary, Sprint 3.23).
    """
    record = session.get(ECGRecord, upstream.ecg_record_id)
    record.record_id = None
    record.storage_path = "/uploads/ecg-1.csv"
    session.flush()

    with pytest.raises(ECGArtifactUnavailableError):
        ECGArtifactRepository(store=artifact_store).load_bundle(record)


def test_missing_artifact_directory_is_reported(session, upstream, artifact_store):
    record = session.get(ECGRecord, upstream.ecg_record_id)

    with pytest.raises(
        ECGArtifactUnavailableError,
        match=r"Required artifact 'waveform/waveform\.npz' is missing",
    ):
        ECGArtifactRepository(store=artifact_store).load_bundle(record)


def test_missing_waveform_artifact_is_a_critical_failure(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    (artifact_store.record_dir(upstream.canonical_record_id) / WAVEFORM_ARTIFACT).unlink()
    record = session.get(ECGRecord, upstream.ecg_record_id)

    with pytest.raises(ECGArtifactUnavailableError, match="waveform.npz"):
        ECGArtifactRepository(store=artifact_store).load_bundle(record)


def test_missing_waveform_descriptor_is_a_critical_failure(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    (artifact_store.record_dir(upstream.canonical_record_id) / WAVEFORM_DESCRIPTOR_ARTIFACT).unlink()
    record = session.get(ECGRecord, upstream.ecg_record_id)

    with pytest.raises(ECGArtifactUnavailableError, match="waveform_meta.json"):
        ECGArtifactRepository(store=artifact_store).load_bundle(record)


def test_an_unreadable_document_is_raised_rather_than_silently_dropped(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    manifest = artifact_store.record_dir(upstream.canonical_record_id) / "manifest" / "manifest.json"
    manifest.write_text("{ this is not valid json", encoding="utf-8")
    record = session.get(ECGRecord, upstream.ecg_record_id)

    with pytest.raises(ECGArtifactUnavailableError, match="could not be read"):
        ECGArtifactRepository(store=artifact_store).load_bundle(record)
