"""ReportGenerationJob ORM model (Sprint 2.17).

Tracks one asynchronous report generation request from submission through
execution to completion: its lifecycle state, current stage, progress, retry
count, failure information and full stage execution history (Sprint 3.11 /
3.13 / 10.13).

The job never stores clinical content -- it is an execution record. The
report it produces is a separate ``GeneratedReport`` row that references the
job.

Tenancy and lineage are captured with real foreign keys so a job can never
reference an ECG recording, patient, organisation or user that does not
exist. ``ecg_record_id`` is the primary integration key of the subsystem: a
report always belongs to a specific recording, never to a patient in general.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.reporting.constants import JobStatus
from app.reporting.models.identifiers import new_job_id


class ReportGenerationJob(Base):
    """One asynchronous report generation request and its execution state."""

    __tablename__ = "report_generation_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_job_id)

    # ── Lineage (Sprint 2.17: reporting references, never duplicates, upstream records) ──
    ecg_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("ecg_records.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    patient_id: Mapped[str] = mapped_column(
        String, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    organisation_id: Mapped[str] = mapped_column(
        String, ForeignKey("organisations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    requested_by_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    requested_by_doctor_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("doctors.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # ── Execution state (Sprint 3.12 / 10.6; transitioned only by the orchestrator) ──
    status: Mapped[str] = mapped_column(String, index=True, nullable=False, default=JobStatus.REQUESTED.value)
    current_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Stage execution history (Sprint 3.11 / 10.13): list of StageExecution dicts ──
    stage_history: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # ── Failure information (Sprint 10.12) ──
    failed_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Provenance and timestamps (Sprint 10.25) ──
    pipeline_version: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
