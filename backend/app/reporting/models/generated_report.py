"""GeneratedReport ORM model (Sprint 2.17 / 2.20 / 3.18).

One row represents one immutable, versioned report generation for one ECG
recording. A single generation produces *both* approved report variants --
Summary and Detailed -- from one Generation Context, so both template
identities are recorded on the same row; the rendered documents themselves
are ``ReportArtifact`` rows.

Immutability (Sprint 2.24 / 3.18): a generated report is never edited.
Regeneration creates a new row with the next ``version`` for the same
``ecg_record_id``; previous versions remain untouched for auditability. The
only field that changes after creation is the lifecycle ``status``, which the
Workflow Orchestrator advances as rendering and storage complete.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.reporting.constants import ReportStatus
from app.reporting.models.identifiers import new_report_id


class GeneratedReport(Base):
    """An immutable, versioned report produced by one report generation job."""

    __tablename__ = "generated_reports"
    __table_args__ = (
        # Report versions are sequential per recording (Sprint 3.18). The
        # constraint is what actually guarantees uniqueness under concurrent
        # generation requests for the same recording.
        UniqueConstraint("ecg_record_id", "version", name="uq_generated_reports_ecg_record_version"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_report_id)

    # ── Owning job: exactly one generated report per job (Sprint 9.18) ──
    job_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("report_generation_jobs.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )

    # ── Lineage ──
    ecg_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("ecg_records.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    patient_id: Mapped[str] = mapped_column(
        String, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    organisation_id: Mapped[str] = mapped_column(
        String, ForeignKey("organisations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    doctor_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("doctors.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # ── Report identity and lifecycle ──
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, index=True, nullable=False, default=ReportStatus.GENERATING.value)

    # ── Template provenance, one pair per approved report variant (Sprint 6.12) ──
    summary_template_id: Mapped[str] = mapped_column(String, nullable=False)
    summary_template_version: Mapped[str] = mapped_column(String, nullable=False)
    detailed_template_id: Mapped[str] = mapped_column(String, nullable=False)
    detailed_template_version: Mapped[str] = mapped_column(String, nullable=False)

    # ── Generation provenance (Sprint 3.18 / 9.9 / 12.10) ──
    pipeline_version: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)
    software_version: Mapped[str] = mapped_column(String, nullable=False)
    #: Clinical rule set version; NULL until the Rules Engine runs (Phase 2).
    rules_version: Mapped[str | None] = mapped_column(String, nullable=True)
    #: AI narrative model version; NULL when no narrative was generated (Phase 3).
    narrative_model_version: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Storage and timestamps ──
    #: Root location under which this report version's artifacts are stored.
    storage_dir: Mapped[str] = mapped_column(String, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
