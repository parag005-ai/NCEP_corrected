"""Pydantic schemas. All responses use camelCase keys to match the frontend TS types."""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


def _empty_str_to_none(value: object) -> object:
    return None if isinstance(value, str) and value.strip() == "" else value


# A still-unmigrated frontend may send "" for an unset optional date field;
# treat that the same as omitting it rather than failing date parsing.
OptionalDate = Annotated[date | None, BeforeValidator(_empty_str_to_none)]


# ────────── Auth ──────────
class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(CamelModel):
    current_password: str
    new_password: str


class PasswordResetRequest(CamelModel):
    email: str


class PasswordResetRequestResponse(CamelModel):
    message: str


class Session(CamelModel):
    user_id: str
    email: str
    name: str
    role: str
    organisation_id: str
    patient_id: str | None = None
    doctor_id: str | None = None
    avatar_url: str | None = None


class LoginResponse(CamelModel):
    # The JWT itself never appears in a JS-readable response body -- it only
    # ever leaves the server as the httpOnly session cookie (see auth.py).
    session: Session


# ────────── Organisation ──────────
class OrganisationBase(CamelModel):
    name: str
    address: str = ""
    contact: str = ""
    admin_id: str = ""
    status: str = "Active"
    total_users: int = 0
    total_patients: int = 0
    plan: str | None = None
    logo_url: str | None = None


class OrganisationCreate(OrganisationBase):
    id: str | None = None


class OrganisationUpdate(CamelModel):
    name: str | None = None
    address: str | None = None
    contact: str | None = None
    admin_id: str | None = None
    status: str | None = None
    total_users: int | None = None
    total_patients: int | None = None
    plan: str | None = None
    logo_url: str | None = None


class OrganisationOut(OrganisationBase):
    id: str
    created_at: datetime | None = None


# ────────── User ──────────
class UserBase(CamelModel):
    email: str
    name: str
    role: str
    organisation_id: str = ""
    status: str = "Active"
    avatar_url: str | None = None
    phone: str | None = None


class UserCreate(UserBase):
    id: str | None = None
    # Required to actually create a user; optional here only so the same
    # schema can back the idempotent PUT upsert, where an update with no
    # password field must leave the existing password hash untouched (see
    # upsert_user in routers/users.py, which enforces this at the route
    # level rather than in the schema).
    password: str | None = None


class UserUpdate(CamelModel):
    email: str | None = None
    name: str | None = None
    role: str | None = None
    organisation_id: str | None = None
    status: str | None = None
    avatar_url: str | None = None
    phone: str | None = None


class UserOut(UserBase):
    id: str
    last_active: datetime | None = None
    created_at: datetime | None = None


# ────────── Doctor ──────────
class DoctorBase(CamelModel):
    user_id: str = ""
    name: str
    email: str = ""
    staff_id: str = ""
    role: str = "Doctor"
    speciality: str = ""
    organisation_id: str = ""
    status: str = "Active"
    assigned_patient_count: int = 0
    phone: str | None = None


class DoctorCreate(DoctorBase):
    id: str | None = None


class DoctorUpdate(CamelModel):
    name: str | None = None
    email: str | None = None
    staff_id: str | None = None
    role: str | None = None
    speciality: str | None = None
    organisation_id: str | None = None
    status: str | None = None
    assigned_patient_count: int | None = None
    phone: str | None = None


class DoctorOut(DoctorBase):
    id: str
    last_active: datetime | None = None
    created_at: datetime | None = None


# ────────── Patient ──────────
class PatientBase(CamelModel):
    name: str
    date_of_birth: OptionalDate = None
    age: int = 0
    gender: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    assigned_doctor_id: str | None = None
    assigned_doctor: str = ""
    organisation_id: str = ""
    status: str = "Stable"
    medical_notes: str = ""


class PatientCreate(PatientBase):
    id: str | None = None


class PatientUpdate(CamelModel):
    name: str | None = None
    date_of_birth: OptionalDate = None
    age: int | None = None
    gender: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    assigned_doctor_id: str | None = None
    assigned_doctor: str | None = None
    organisation_id: str | None = None
    status: str | None = None
    medical_notes: str | None = None


class PatientOut(PatientBase):
    id: str
    created_at: datetime | None = None


class PatientLinkRequest(CamelModel):
    """organisation_id is only read for superadmin callers -- everyone else is
    linked to their own organisation regardless of what's sent here."""

    organisation_id: str | None = None


# ────────── ECG Record ──────────
class ECGRecordBase(CamelModel):
    patient_id: str = ""
    patient_name: str = ""
    doctor_id: str = ""
    organisation_id: str = ""
    file_name: str = ""
    file_type: str = ""
    recording_date: OptionalDate = None
    device_source: str = ""
    notes: str = ""
    status: str = "Uploaded"
    uploaded_by: str = ""


class ECGRecordCreate(ECGRecordBase):
    pass


class ECGRecordUpdate(CamelModel):
    status: str | None = None
    notes: str | None = None
    recording_date: OptionalDate = None
    device_source: str | None = None


class ECGRecordOut(ECGRecordBase):
    id: str
    uploaded_at: datetime | None = None
    source_format: str | None = None
    sampling_rate_hz: float | None = None
    lead_count: int | None = None
    available_leads: list[str] | None = None
    xyz_available: bool = False
    duration_seconds: float | None = None
    sample_count: int | None = None
    units: str | None = None
    record_id: str | None = None
    record_dir: str | None = None
    validation_status: str | None = None
    validation_issues: list[dict] | None = None
    quality_score: float | None = None
    quality_flags: list[str] | None = None
    beat_count: int | None = None


class ECGIngestJobOut(CamelModel):
    id: str
    status: str
    current_stage: str | None = None
    attempt_count: int
    ecg_record_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status_url: str


class WaveformResponse(CamelModel):
    ecg_record_id: str
    sampling_rate_hz: float | None = None
    leads: list[str]
    point_count: int
    downsample_factor: int
    time_s: list[float]
    signals: dict[str, list[float]]


# ────────── Clinical Report ──────────
class ReportBase(CamelModel):
    title: str = ""
    patient_id: str = ""
    patient_name: str = ""
    doctor_id: str = ""
    doctor_name: str = ""
    organisation_id: str = ""
    ecg_record_id: str = ""
    clinical_observations: str = ""
    findings: str = ""
    interpretation: str = ""
    recommendations: str = ""
    status: str = "Draft"
    reviewed_by: str = ""
    shared_with_patient: bool = False


class ReportCreate(ReportBase):
    id: str | None = None


class ReportUpdate(CamelModel):
    title: str | None = None
    clinical_observations: str | None = None
    findings: str | None = None
    interpretation: str | None = None
    recommendations: str | None = None
    status: str | None = None
    reviewed_by: str | None = None
    shared_with_patient: bool | None = None


class ReportOut(ReportBase):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ────────── Legal Consent ──────────
class LegalConsentStatus(CamelModel):
    accepted: bool
    version: str | None = None
    accepted_at: datetime | None = None


class LegalConsentAccept(CamelModel):
    version: str = "1"


# ────────── Usage ──────────
class UsageRecordBase(CamelModel):
    action: str = ""
    credits_used: float = 0
    organisation_id: str = ""
    organisation_name: str = ""
    doctor_id: str | None = None
    doctor_name: str | None = None
    status: str = "Success"


class UsageRecordCreate(UsageRecordBase):
    id: str | None = None


class UsageRecordOut(UsageRecordBase):
    id: str
    timestamp: datetime | None = None


# ────────── System Administration ──────────
class ApplicationDataResetResponse(CamelModel):
    ok: bool
    reset_at: datetime


# ────────── Pipeline Report Data ──────────
class ClinicalFlag(CamelModel):
    name: str
    result: str
    description: str = ""


class SaecgParameter(CamelModel):
    name: str
    value: str
    unit: str = ""
    interpretation: str = ""
    score: float


class PipelineReportData(CamelModel):
    """Signal-processing output for one ECG record, keyed to the same id as
    the record itself. Fields this pipeline does not yet compute (SAECG late-
    potential parameters, QT/repolarization analysis) are surfaced as empty/
    null rather than fabricated -- see reports.py:get_pipeline_report."""

    processing_id: str
    diagnostic_level: str = "Automated"
    clinical_unit: str = ""
    platform_name: str = "CardioNexus"
    patient_name: str = ""
    age_sex: str = ""
    patient_id: str = ""
    lead_name: str = ""
    recording_duration: str = ""
    report_date: str = ""
    physician: str = ""
    preprocessing_status: str
    analysis_status: str
    signal_quality_score: float = 0
    r_peak_count: int = 0
    qrs_complexes: int = 0
    qrs_note: str = ""
    mean_heart_rate: float = 0
    clinical_flags: list[ClinicalFlag] = []
    saecg_parameters: list[SaecgParameter] = []
    qt_interval: float | None = None
    qtc_bazett: float | None = None
    qt_dispersion: float | None = None
    tpeak_tend: float | None = None
    tpe_qt_ratio: float | None = None
    t_wave_dispersion: float | None = None
    qtc_highlighted: bool = False
    clinical_insight: str = ""
    confidence_score: str = "Low"
    automated_analysis: str = ""
    physician_name: str = ""
    physician_title: str = ""


# ────────── Audit Log ──────────
class AuditLogBase(CamelModel):
    event: str = ""
    event_type: str = ""
    actor_id: str = ""
    actor_name: str = ""
    actor_role: str = ""
    organisation_id: str = ""
    organisation_name: str = ""
    resource: str = ""
    result: str = "Success"
    ip_address: str = ""
    details: str = ""


class AuditLogCreate(AuditLogBase):
    id: str | None = None


class AuditLogOut(AuditLogBase):
    id: str
    timestamp: datetime | None = None
