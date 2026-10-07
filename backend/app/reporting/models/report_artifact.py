"""ReportArtifact ORM model (Sprint 2.19 / 9.7).

Every output produced by a report generation -- Summary/Detailed HTML,
Summary/Detailed PDF, the raw ECG SVG, metadata and manifest documents -- is
registered here with the metadata required for traceability, integrity
verification and reproducibility.

This row is the artifact *registry entry*; the bytes live in the reporting
artifact store and are located by ``storage_location`` (relative to the
owning report's ``storage_dir``), keeping the registry independent of the
storage backend (Sprint 9.10).

Registered artifacts are immutable (Sprint 9.8). Only ``status`` advances
along the artifact lifecycle after registration.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.reporting.constants import ArtifactStatus
from app.reporting.models.identifiers import new_artifact_id


class ReportArtifact(Base):
    """A registered, checksum-protected asset belonging to one generated report."""

    __tablename__ = "report_artifacts"
    __table_args__ = (
        # One registry entry per stored file within a report version.
        UniqueConstraint("report_id", "storage_location", name="uq_report_artifacts_report_location"),
        Index("ix_report_artifacts_report_id_artifact_type", "report_id", "artifact_type"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_artifact_id)

    #: Artifacts are owned by their report version and are removed with it.
    report_id: Mapped[str] = mapped_column(
        String, ForeignKey("generated_reports.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: Denormalized recording identifier (Sprint 9.7) -- lets artifacts be
    #: traced to a recording without joining through the report.
    ecg_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("ecg_records.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    artifact_type: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    #: Path of the stored file relative to the owning report's storage_dir.
    storage_location: Mapped[str] = mapped_column(String, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default=ArtifactStatus.REGISTERED.value)

    #: Artifact-specific facts that do not apply to every artifact type, e.g.
    #: the lead and time window a visualization shows (Sprint 4.12). NULL for
    #: artifacts that carry none. Never used for lineage or access control --
    #: those are columns.
    artifact_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
