"""Unit tests for the ECG domain model package (app.ecg.models) and lead mapping."""

from __future__ import annotations

import numpy as np
import pytest

from app.ecg.constants import CanonicalLead, ECGFormat
from app.ecg.lead_mapping import UnmappableLeadError, resolve_canonical_lead, try_resolve_canonical_lead
from app.ecg.models import (
    ECGMetadata,
    ECGRecord,
    LeadSignal,
    PatientMetadata,
    Waveform,
)
from app.ecg.models.annotations import Annotations
from app.ecg.models.clinical_metadata import ClinicalMetadata
from app.ecg.models.device_metadata import DeviceMetadata
from app.ecg.models.quality_metadata import QualityMetadata
from app.ecg.models.source_information import SourceInformation


# -- lead mapping -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("I", CanonicalLead.I),
        ("lead i", CanonicalLead.I),
        ("Lead aVR", CanonicalLead.aVR),
        ("V1", CanonicalLead.V1),
        ("vx", CanonicalLead.X),
        ("Frank Z", CanonicalLead.Z),
    ],
)
def test_resolve_canonical_lead_happy_path(raw: str, expected: CanonicalLead) -> None:
    assert resolve_canonical_lead(raw) == expected


def test_resolve_canonical_lead_unmappable_raises() -> None:
    with pytest.raises(UnmappableLeadError):
        resolve_canonical_lead("V7")


def test_try_resolve_canonical_lead_returns_none_for_unknown() -> None:
    assert try_resolve_canonical_lead("not-a-lead") is None


# -- Waveform -------------------------------------------------------------


def test_waveform_happy_path() -> None:
    waveform = Waveform(
        leads={CanonicalLead.I: LeadSignal(CanonicalLead.I, np.zeros(500))},
        sampling_rate_hz=500,
    )
    assert waveform.sample_count == 500
    assert waveform.duration_seconds == 1.0
    assert waveform.lead_count == 1
    assert waveform.xyz_available is False
    assert waveform.available_leads == (CanonicalLead.I,)


def test_waveform_xyz_available_when_any_frank_lead_present() -> None:
    waveform = Waveform(
        leads={
            CanonicalLead.I: LeadSignal(CanonicalLead.I, np.zeros(10)),
            CanonicalLead.X: LeadSignal(CanonicalLead.X, np.zeros(10)),
        },
        sampling_rate_hz=100,
    )
    assert waveform.xyz_available is True


def test_waveform_rejects_empty_leads() -> None:
    with pytest.raises(ValueError):
        Waveform(leads={}, sampling_rate_hz=500)


def test_waveform_rejects_non_positive_sampling_rate() -> None:
    with pytest.raises(ValueError):
        Waveform(leads={CanonicalLead.I: LeadSignal(CanonicalLead.I, np.zeros(10))}, sampling_rate_hz=0)


def test_waveform_rejects_mismatched_sample_counts() -> None:
    with pytest.raises(ValueError):
        Waveform(
            leads={
                CanonicalLead.I: LeadSignal(CanonicalLead.I, np.zeros(10)),
                CanonicalLead.II: LeadSignal(CanonicalLead.II, np.zeros(20)),
            },
            sampling_rate_hz=500,
        )


def test_lead_signal_rejects_multidimensional_samples() -> None:
    with pytest.raises(ValueError):
        LeadSignal(CanonicalLead.I, np.zeros((10, 2)))


def test_waveform_leads_are_immutable_samples() -> None:
    waveform = Waveform(leads={CanonicalLead.I: LeadSignal(CanonicalLead.I, np.zeros(10))}, sampling_rate_hz=500)
    with pytest.raises(ValueError):
        waveform.leads[CanonicalLead.I].samples[0] = 1.0


# -- PatientMetadata -------------------------------------------------------------


def test_patient_metadata_missing_fields_and_is_empty() -> None:
    patient = PatientMetadata()
    assert patient.is_empty()
    assert "patient_id" in patient.missing_fields()

    partial = PatientMetadata(patient_id="P1", age=40)
    assert not partial.is_empty()
    assert "patient_id" not in partial.missing_fields()
    assert "sex" in partial.missing_fields()


# -- ECGRecord -------------------------------------------------------------


def _build_minimal_record() -> ECGRecord:
    waveform = Waveform(leads={CanonicalLead.I: LeadSignal(CanonicalLead.I, np.zeros(500))}, sampling_rate_hz=500)
    ecg_metadata = ECGMetadata(
        record_id="rec-1",
        source_format=ECGFormat.CSV,
        sampling_rate_hz=500,
        lead_count=1,
        available_leads=(CanonicalLead.I,),
        xyz_available=False,
        recording_duration_seconds=1.0,
        sample_count=500,
        units="mV",
    )
    return ECGRecord(
        record_id="rec-1",
        waveform=waveform,
        patient_metadata=PatientMetadata(),
        ecg_metadata=ecg_metadata,
        clinical_metadata=ClinicalMetadata(),
        device_metadata=DeviceMetadata(),
        quality_metadata=QualityMetadata(),
        annotations=Annotations(),
        source_information=SourceInformation(upload_id="u1", source_format=ECGFormat.CSV),
    )


def test_ecg_record_aggregates_all_required_components() -> None:
    record = _build_minimal_record()
    assert record.record_id == "rec-1"
    assert record.ecg_metadata.source_format == ECGFormat.CSV
    assert record.patient_metadata.is_empty()
    assert record.annotations.is_empty()


def test_ecg_record_is_frozen() -> None:
    record = _build_minimal_record()
    with pytest.raises(Exception):  # dataclasses.FrozenInstanceError subclasses AttributeError
        record.record_id = "other"  # type: ignore[misc]
