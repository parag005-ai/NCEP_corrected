"""Tests for the tenant-safe Generation Context Loader (Sprint 3.6)."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import Doctor, ECGRecord, Organisation, Patient, User
from app.reporting.constants import (
    REPORT_PIPELINE_VERSION,
    REPORT_SCHEMA_VERSION,
    REPORTING_SOFTWARE_VERSION,
    SectionStatus,
)
from app.reporting.context import GenerationContextLoader
from app.reporting.exceptions import (
    ECGArtifactUnavailableError,
    ECGRecordNotFoundError,
    InconsistentContextError,
    ReportAccessDeniedError,
    UpstreamRecordMissingError,
)
from app.reporting.repositories import ECGArtifactRepository, ReportGenerationJobRepository

from tests.reporting.conftest import UpstreamFixture, write_canonical_artifacts
from tests.reporting.test_repositories import make_report


def build_loader(session: Session, artifact_store) -> GenerationContextLoader:
    return GenerationContextLoader(session, artifacts=ECGArtifactRepository(store=artifact_store))


def make_job(
    session: Session,
    upstream: UpstreamFixture,
    *,
    requested_by_user_id: str | None = None,
    patient_id: str | None = None,
    organisation_id: str | None = None,
):
    return ReportGenerationJobRepository(session).create(
        ecg_record_id=upstream.ecg_record_id,
        patient_id=patient_id or upstream.patient_id,
        organisation_id=organisation_id or upstream.organisation_id,
        requested_by_user_id=requested_by_user_id or upstream.user_id,
        requested_by_doctor_id=upstream.doctor_id,
    )


def add_user(session: Session, *, user_id: str, role: str, organisation_id: str, email: str) -> User:
    user = User(
        id=user_id,
        email=email,
        name=f"User {user_id}",
        role=role,
        organisation_id=organisation_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def loaded_context(session, upstream, artifact_store):
    """A context loaded from a fully ingested recording."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    job = make_job(session, upstream)
    return build_loader(session, artifact_store).load(job)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_context_carries_the_administrative_identity_of_the_generation(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    job = make_job(session, upstream)

    context = build_loader(session, artifact_store).load(job)

    assert context.generation.job_id == job.id
    assert context.generation.ecg_record_id == upstream.ecg_record_id
    assert context.generation.requested_by_user_id == upstream.user_id
    assert context.generation.report_version == 1
    assert context.generation.pipeline_version == REPORT_PIPELINE_VERSION
    assert context.generation.schema_version == REPORT_SCHEMA_VERSION
    assert context.generation.software_version == REPORTING_SOFTWARE_VERSION
    assert context.generation.generated_at.tzinfo is not None


def test_report_version_follows_the_existing_report_history(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    make_report(session, upstream, version=1)
    session.commit()

    context = build_loader(session, artifact_store).load(make_job(session, upstream))

    assert context.generation.report_version == 2


def test_context_carries_organisation_patient_and_doctor(loaded_context, upstream):
    assert loaded_context.organisation.organisation_id == upstream.organisation_id
    assert loaded_context.organisation.name == "Test Hospital"
    assert loaded_context.patient.patient_id == upstream.patient_id
    assert loaded_context.patient.name == "Test Patient"
    assert loaded_context.doctor is not None
    assert loaded_context.doctor.doctor_id == upstream.doctor_id


def test_context_carries_the_recording_and_its_ingestion_quality_summary(loaded_context, upstream):
    ecg = loaded_context.ecg

    assert ecg.ecg_record_id == upstream.ecg_record_id
    assert ecg.canonical_record_id == upstream.canonical_record_id
    assert ecg.sampling_rate_hz == 1000.0
    assert ecg.available_leads == ("I", "II", "V1")
    assert ecg.duration_seconds == 10.0
    assert ecg.units == "mV"
    # Produced by ingestion preprocessing, not by the reporting subsystem.
    assert ecg.quality.quality_score == 0.93
    assert ecg.quality.quality_flags == ("baseline_drift",)
    assert ecg.quality.beat_count == 12
    assert ecg.quality.validation_status == "PASS"


def test_context_carries_the_canonical_ecg_artifacts(loaded_context, upstream):
    assert loaded_context.artifacts.waveform.size_bytes > 0
    assert loaded_context.artifacts.waveform_descriptor["units"] == "mV"
    assert "ecg_metadata" in loaded_context.artifacts.metadata_documents
    assert loaded_context.artifacts.manifest["record_id"] == upstream.canonical_record_id


def test_signal_processing_measurement_sections_are_populated(loaded_context):
    """Phase 2: the vendored ECG pipeline runs against the recording's real
    waveform, so most Signal Processing sections carry a real payload.

    Individual metrics inside a populated section may still be None for this
    particular (synthetic, non-physiological) test waveform -- e.g. it has no
    real P/T-wave morphology for delineation to find -- which is the
    NOT_AVAILABLE case (data source exists, holds nothing for this
    recording), distinct from AWAITING_SIGNAL_PROCESSING (not computed at
    all). See app/signal_processing/README.md.
    """
    signal_processing = loaded_context.signal_processing
    assert signal_processing.is_available

    for section in (
        signal_processing.ecg_parameters,
        signal_processing.clinical_measurements,
        signal_processing.signal_quality_metrics,
        signal_processing.beat_selection,
    ):
        assert section.is_available
        assert section.payload is not None

    # Classification/scoring and narrative interpretation require the medical
    # team's confirmed thresholds and are deliberately not authored --
    # unaffected by this integration.
    assert not signal_processing.clinical_findings.is_available
    assert signal_processing.clinical_findings.status is SectionStatus.NOT_AVAILABLE
    # No plotting/annotation code was delivered alongside the pipeline.
    assert not signal_processing.waveform_annotations.is_available
    assert signal_processing.waveform_annotations.status is SectionStatus.NOT_AVAILABLE


def test_signal_processing_falls_back_to_awaiting_when_waveform_is_unreadable(
    session, upstream, artifact_store
):
    """A corrupt/unreadable waveform degrades Signal Processing to the Phase 1
    all-awaiting state rather than failing report generation outright."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id, waveform_bytes=b"not a real npz")
    job = make_job(session, upstream)

    context = build_loader(session, artifact_store).load(job)

    assert not context.signal_processing.is_available
    assert all(section.payload is None for section in context.signal_processing.sections)


def test_the_loaded_context_is_immutable(loaded_context):
    with pytest.raises(dataclasses.FrozenInstanceError):
        loaded_context.patient = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        loaded_context.ecg.sampling_rate_hz = 500.0
    with pytest.raises(TypeError):
        loaded_context.artifacts.waveform_descriptor["units"] = "uV"


# ---------------------------------------------------------------------------
# Missing upstream records
# ---------------------------------------------------------------------------


def test_a_deleted_recording_stops_generation(session, upstream, artifact_store):
    job = make_job(session, upstream)
    job.ecg_record_id = "ecg-removed"

    with pytest.raises(ECGRecordNotFoundError):
        build_loader(session, artifact_store).load(job)


def test_a_deleted_requester_stops_generation(session, upstream, artifact_store):
    job = make_job(session, upstream)
    job.requested_by_user_id = "usr-removed"

    with pytest.raises(UpstreamRecordMissingError):
        build_loader(session, artifact_store).load(job)


def test_a_missing_patient_stops_generation(session, upstream, artifact_store):
    """Defensive path: RESTRICT foreign keys make a truly deleted patient impossible,
    so the absence is simulated in memory rather than persisted."""
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    job = make_job(session, upstream)
    job.patient_id = "pat-removed"
    session.get(ECGRecord, upstream.ecg_record_id).patient_id = "pat-removed"

    with pytest.raises(UpstreamRecordMissingError):
        build_loader(session, artifact_store).load(job)


def test_missing_canonical_artifacts_stop_generation(session, upstream, artifact_store):
    job = make_job(session, upstream)

    with pytest.raises(ECGArtifactUnavailableError):
        build_loader(session, artifact_store).load(job)


# ---------------------------------------------------------------------------
# Authorization (Sprint 10.10 / 10.24)
# ---------------------------------------------------------------------------


def test_staff_from_another_organisation_are_refused(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    session.add(Organisation(id="org-2", name="Other Hospital", created_at=datetime.now(timezone.utc)))
    session.flush()
    outsider = add_user(session, user_id="usr-2", role="doctor", organisation_id="org-2",
                        email="outsider@example.test")
    job = make_job(session, upstream, requested_by_user_id=outsider.id)

    with pytest.raises(ReportAccessDeniedError, match="another organisation"):
        build_loader(session, artifact_store).load(job)


def test_a_superadmin_may_generate_across_organisations(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    session.add(Organisation(id="org-2", name="Other Hospital", created_at=datetime.now(timezone.utc)))
    session.flush()
    superadmin = add_user(session, user_id="usr-super", role="superadmin", organisation_id="org-2",
                          email="super@example.test")
    job = make_job(session, upstream, requested_by_user_id=superadmin.id)

    context = build_loader(session, artifact_store).load(job)

    assert context.generation.requested_by_user_id == superadmin.id


def test_a_patient_may_only_reach_their_own_recording(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    owner = add_user(session, user_id="usr-pat", role="patient", organisation_id=upstream.organisation_id,
                     email="patient@example.test")
    stranger = add_user(session, user_id="usr-pat-2", role="patient",
                        organisation_id=upstream.organisation_id, email="stranger@example.test")

    context = build_loader(session, artifact_store).load(
        make_job(session, upstream, requested_by_user_id=owner.id)
    )
    assert context.patient.patient_id == upstream.patient_id

    with pytest.raises(ReportAccessDeniedError, match="another patient"):
        build_loader(session, artifact_store).load(
            make_job(session, upstream, requested_by_user_id=stranger.id)
        )


def test_an_unknown_role_may_not_generate_reports(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    technician = add_user(session, user_id="usr-tech", role="technician",
                          organisation_id=upstream.organisation_id, email="tech@example.test")
    job = make_job(session, upstream, requested_by_user_id=technician.id)

    with pytest.raises(ReportAccessDeniedError, match="may not access ECG recordings"):
        build_loader(session, artifact_store).load(job)


# ---------------------------------------------------------------------------
# Lineage consistency (Sprint 5.12 / 5.13)
# ---------------------------------------------------------------------------


def test_a_job_pointing_at_another_patient_is_refused(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    session.add(Patient(id="pat-2", name="Other Patient", email="other@example.test",
                        organisation_id=upstream.organisation_id, created_at=datetime.now(timezone.utc)))
    session.flush()
    job = make_job(session, upstream, patient_id="pat-2")

    with pytest.raises(InconsistentContextError, match="patient"):
        build_loader(session, artifact_store).load(job)


def test_a_job_pointing_at_another_organisation_is_refused(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    session.add(Organisation(id="org-2", name="Other Hospital", created_at=datetime.now(timezone.utc)))
    session.flush()
    job = make_job(session, upstream, organisation_id="org-2")

    with pytest.raises(InconsistentContextError, match="organisation"):
        build_loader(session, artifact_store).load(job)


def test_a_patient_from_another_organisation_is_refused(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    session.add(Organisation(id="org-2", name="Other Hospital", created_at=datetime.now(timezone.utc)))
    session.flush()
    job = make_job(session, upstream)
    session.get(Patient, upstream.patient_id).organisation_id = "org-2"

    with pytest.raises(InconsistentContextError, match="Patient"):
        build_loader(session, artifact_store).load(job)


def test_a_doctor_from_another_organisation_is_refused(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    session.add(Organisation(id="org-2", name="Other Hospital", created_at=datetime.now(timezone.utc)))
    session.flush()
    job = make_job(session, upstream)
    session.get(Doctor, upstream.doctor_id).organisation_id = "org-2"

    with pytest.raises(InconsistentContextError, match="Doctor"):
        build_loader(session, artifact_store).load(job)


# ---------------------------------------------------------------------------
# Recoverable gaps (Sprint 3.14)
# ---------------------------------------------------------------------------


def test_an_unresolvable_doctor_yields_a_context_without_doctor(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    job = make_job(session, upstream)
    record = session.get(ECGRecord, upstream.ecg_record_id)
    record.doctor_id = ""
    session.get(Patient, upstream.patient_id).assigned_doctor_id = None
    session.flush()

    context = build_loader(session, artifact_store).load(job)

    assert context.doctor is None


def test_the_patients_assigned_doctor_is_the_fallback(session, upstream, artifact_store):
    write_canonical_artifacts(artifact_store, upstream.canonical_record_id)
    job = make_job(session, upstream)
    session.get(ECGRecord, upstream.ecg_record_id).doctor_id = ""
    session.flush()

    context = build_loader(session, artifact_store).load(job)

    assert context.doctor is not None
    assert context.doctor.doctor_id == upstream.doctor_id
