"""SQLAlchemy models mirroring the frontend TypeScript types (see NCEPdemo/src/types)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, default="")
    contact: Mapped[str] = mapped_column(String, default="")
    admin_id: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    total_patients: Mapped[int] = mapped_column(Integer, default=0)
    plan: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    organisation_id: Mapped[str] = mapped_column(
        String, ForeignKey("organisations.id", ondelete="RESTRICT"), index=True, default=""
    )
    status: Mapped[str] = mapped_column(String, default="Active")
    last_active: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str] = mapped_column(String, default="")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, default="")
    staff_id: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="Doctor")
    speciality: Mapped[str] = mapped_column(String, default="")
    organisation_id: Mapped[str] = mapped_column(
        String, ForeignKey("organisations.id", ondelete="RESTRICT"), index=True, default=""
    )
    status: Mapped[str] = mapped_column(String, default="Active")
    assigned_patient_count: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    phone: Mapped[str | None] = mapped_column(String, nullable=True)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    age: Mapped[int] = mapped_column(Integer, default=0)
    gender: Mapped[str] = mapped_column(String, default="")
    email: Mapped[str] = mapped_column(String, unique=True, index=True, default="")
    phone: Mapped[str] = mapped_column(String, default="")
    address: Mapped[str] = mapped_column(String, default="")
    assigned_doctor_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("doctors.id", ondelete="SET NULL"), index=True, nullable=True
    )
    assigned_doctor: Mapped[str] = mapped_column(String, default="")
    organisation_id: Mapped[str] = mapped_column(
        String, ForeignKey("organisations.id", ondelete="RESTRICT"), index=True, default=""
    )
    status: Mapped[str] = mapped_column(String, default="Stable")
    medical_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PatientOrganisationLink(Base):
    """Grants an organisation other than the patient's home one (Patient.organisation_id,
    unchanged by this) read access to that patient and their existing ECG records/reports --
    e.g. a patient who is now also seen at a second hospital, added there by ID rather than
    re-registered. Nothing about the patient row itself, or their prior clinical data's
    organisation_id, changes; this only widens who may read it."""

    __tablename__ = "patient_organisation_links"
    __table_args__ = (UniqueConstraint("patient_id", "organisation_id", name="uq_patient_org_link"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        String, ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    organisation_id: Mapped[str] = mapped_column(
        String, ForeignKey("organisations.id", ondelete="CASCADE"), index=True
    )
    linked_by_user_id: Mapped[str] = mapped_column(String, default="")
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ECGRecord(Base):
    __tablename__ = "ecg_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        String, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, default=""
    )
    patient_name: Mapped[str] = mapped_column(String, default="")
    doctor_id: Mapped[str] = mapped_column(String, index=True, default="")
    organisation_id: Mapped[str] = mapped_column(
        String, ForeignKey("organisations.id", ondelete="RESTRICT"), index=True, default=""
    )
    file_name: Mapped[str] = mapped_column(String, default="")
    file_type: Mapped[str] = mapped_column(String, default="")
    recording_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    device_source: Mapped[str] = mapped_column(String, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="Uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    uploaded_by: Mapped[str] = mapped_column(String, default="")
    storage_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Waveform signal metadata (parsed from uploaded SAECG/ECG files) ──
    source_format: Mapped[str | None] = mapped_column(String, nullable=True)
    sampling_rate_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_leads: Mapped[list | None] = mapped_column(JSON, nullable=True)
    xyz_available: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    units: Mapped[str | None] = mapped_column(String, nullable=True)
    record_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Ingestion + preprocessing pipeline outcome ──
    record_dir: Mapped[str | None] = mapped_column(String, nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String, nullable=True)
    validation_issues: Mapped[list | None] = mapped_column(JSON, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_flags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    beat_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artifact_manifest: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ECGIngestJob(Base):
    """Persistent identity and terminal outcome for one canonical ECG ingest."""

    __tablename__ = "ecg_ingest_jobs"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_ecg_ingest_jobs_idempotency_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    request_fingerprint: Mapped[str] = mapped_column(String, nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(
        String, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    doctor_id: Mapped[str] = mapped_column(String, default="")
    organisation_id: Mapped[str] = mapped_column(
        String, ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requested_by_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    uploaded_by: Mapped[str] = mapped_column(String, default="")
    upload_id: Mapped[str] = mapped_column(String, nullable=False)
    file_names: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    request_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String, nullable=False, default="QUEUED", index=True)
    current_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ecg_record_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("ecg_records.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClinicalReport(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, default="")
    patient_id: Mapped[str] = mapped_column(
        String, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, default=""
    )
    patient_name: Mapped[str] = mapped_column(String, default="")
    doctor_id: Mapped[str] = mapped_column(String, index=True, default="")
    doctor_name: Mapped[str] = mapped_column(String, default="")
    organisation_id: Mapped[str] = mapped_column(
        String, ForeignKey("organisations.id", ondelete="RESTRICT"), index=True, default=""
    )
    ecg_record_id: Mapped[str] = mapped_column(String, default="")
    clinical_observations: Mapped[str] = mapped_column(Text, default="")
    findings: Mapped[str] = mapped_column(Text, default="")
    interpretation: Mapped[str] = mapped_column(Text, default="")
    recommendations: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="Draft")
    reviewed_by: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    shared_with_patient: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event: Mapped[str] = mapped_column(String, default="")
    event_type: Mapped[str] = mapped_column(String, default="")
    actor_id: Mapped[str] = mapped_column(String, index=True, default="")
    actor_name: Mapped[str] = mapped_column(String, default="")
    actor_role: Mapped[str] = mapped_column(String, default="")
    organisation_id: Mapped[str] = mapped_column(String, index=True, default="")
    organisation_name: Mapped[str] = mapped_column(String, default="")
    resource: Mapped[str] = mapped_column(String, default="")
    result: Mapped[str] = mapped_column(String, default="Success")
    ip_address: Mapped[str] = mapped_column(String, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LegalConsent(Base):
    """One row per user acceptance of the current terms/privacy bundle.

    A user can accept more than once across `version` bumps, so this is an
    append-only log rather than a single mutable flag on User -- `current`
    (GET /api/legal-consents/current) reads the most recent row for the
    caller rather than assuming there is exactly one.
    """

    __tablename__ = "legal_consents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[str] = mapped_column(String, default="1")
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    action: Mapped[str] = mapped_column(String, default="")
    credits_used: Mapped[float] = mapped_column(Float, default=0)
    organisation_id: Mapped[str] = mapped_column(
        String, ForeignKey("organisations.id", ondelete="RESTRICT"), index=True, default=""
    )
    organisation_name: Mapped[str] = mapped_column(String, default="")
    doctor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="Success")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
