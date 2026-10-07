"""API-facing Pydantic schemas for the ECG domain.

These are the objects that cross the REST boundary (Implementation Spec
Chapter 17). They are intentionally distinct from the internal domain
objects in `app.ecg.models`: the domain objects are immutable dataclasses
used inside the ingestion pipeline, while these schemas are what API
routers serialize to clients. Waveform sample data is only ever exposed
through the dedicated waveform schema/endpoint, never embedded in the ECG
summary (17.10).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.ecg.constants import CanonicalLead, ECGFormat, ValidationStatus


class PatientMetadataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str | None = None
    name: str | None = None
    date_of_birth: date | None = None
    age: int | None = None
    sex: str | None = None
    hospital: str | None = None
    clinician: str | None = None
    clinical_history: str | None = None
    missing_fields: tuple[str, ...] = ()


class ECGMetadataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    record_id: str
    source_format: ECGFormat
    sampling_rate_hz: float
    lead_count: int
    available_leads: tuple[CanonicalLead, ...]
    xyz_available: bool
    recording_duration_seconds: float
    sample_count: int
    units: str
    device_manufacturer: str | None = None
    device_model: str | None = None
    gain: float | None = None
    baseline: float | None = None
    filter_settings: str | None = None
    acquisition_timestamp: datetime | None = None
    checksum: str | None = None
    recording_location: str | None = None
    session_id: str | None = None


class ClinicalMetadataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    diagnosis: str | None = None
    reason_for_examination: str | None = None
    medications: tuple[str, ...] = ()
    procedure_notes: str | None = None
    clinical_comments: str | None = None


class DeviceMetadataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    manufacturer: str | None = None
    model: str | None = None
    firmware_version: str | None = None
    serial_number: str | None = None
    software_version: str | None = None


class QualityMetadataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quality_flags: tuple[str, ...] = ()
    noise_indicators: tuple[str, ...] = ()
    device_warnings: tuple[str, ...] = ()
    recording_confidence: float | None = None


class AnnotationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    annotation_type: str
    label: str
    sample_index: int | None = None
    time_offset_seconds: float | None = None
    lead: CanonicalLead | None = None
    source: str | None = None


class SourceInformationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    upload_id: str
    source_format: ECGFormat
    original_filenames: tuple[str, ...] = ()
    parser_name: str = ""
    ingested_at: datetime | None = None


class WaveformSummarySchema(BaseModel):
    """Waveform description without sample data (used inside the ECG summary)."""

    available_leads: tuple[CanonicalLead, ...]
    lead_count: int
    sampling_rate_hz: float
    sample_count: int
    duration_seconds: float
    units: str
    xyz_available: bool


class WaveformDataSchema(BaseModel):
    """Full waveform payload, returned only by the dedicated waveform endpoint."""

    sampling_rate_hz: float
    units: str
    sample_count: int
    leads: dict[CanonicalLead, list[float]]


class ECGRecordSummarySchema(BaseModel):
    """Response body for GET /ecg/{record_id}. Metadata only, no raw samples (17.10)."""

    record_id: str
    waveform: WaveformSummarySchema
    patient_metadata: PatientMetadataSchema
    ecg_metadata: ECGMetadataSchema
    clinical_metadata: ClinicalMetadataSchema
    device_metadata: DeviceMetadataSchema
    quality_metadata: QualityMetadataSchema
    annotations: tuple[AnnotationSchema, ...]
    source_information: SourceInformationSchema


class ValidationIssueSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    validator_name: str
    severity: str
    status: ValidationStatus
    message: str
    recommendation: str | None = None


class ValidationResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: ValidationStatus
    issues: tuple[ValidationIssueSchema, ...] = ()


class ProcessingManifestSchema(BaseModel):
    """Mirrors `app.ingestion.storage.artifacts.ProcessingManifest` exactly."""

    model_config = ConfigDict(from_attributes=True)

    processing_id: str
    upload_id: str
    record_id: str
    source_format: ECGFormat
    parser_name: str
    validation_status: ValidationStatus
    validation_issues: tuple[ValidationIssueSchema, ...] = ()
    processing_started_at: datetime
    processing_completed_at: datetime
    software_version: str
    generated_artifacts: tuple[str, ...] = ()


class UploadResponseSchema(BaseModel):
    upload_id: str
    status: str


class UploadStatusSchema(BaseModel):
    upload_id: str
    state: str
    record_id: str | None = None
    detail: str | None = None
