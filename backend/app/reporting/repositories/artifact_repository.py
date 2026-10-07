"""Persistence for Report Artifacts (Sprint 2.19 / 9.7 / 10.9).

This repository is the authoritative *registry* of generated report assets:
it records artifact identity, type, storage location, size, checksum,
lifecycle status and generation timestamp. It does not read or write artifact
bytes -- persisting the files themselves belongs to the reporting artifact
store, keeping the registry independent of the storage backend (Sprint 9.10).

Registered artifacts are immutable (Sprint 9.8): no method changes an
artifact's type, location, size or checksum after registration; only the
lifecycle ``status`` advances.

Transaction policy: methods flush, never commit; the caller owns the
transaction boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.reporting.constants import ArtifactStatus, ArtifactType
from app.reporting.exceptions import ReportArtifactNotFoundError
from app.reporting.models.generated_report import GeneratedReport
from app.reporting.models.report_artifact import ReportArtifact


class ReportArtifactRepository:
    """Registers and reads ``ReportArtifact`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        *,
        report: GeneratedReport,
        artifact_type: ArtifactType,
        content_type: str,
        storage_location: str,
        file_size_bytes: int,
        checksum_sha256: str,
        status: ArtifactStatus = ArtifactStatus.REGISTERED,
        generated_at: datetime | None = None,
        artifact_metadata: Mapping[str, Any] | None = None,
    ) -> ReportArtifact:
        """Registers one generated asset against its report version.

        ``storage_location`` is relative to the report's ``storage_dir`` and is
        unique within the report; the checksum and size are supplied by the
        stage that produced the file, after it verified the written output
        (Sprint 9.11). ``artifact_metadata`` carries facts specific to the
        artifact type, such as the lead and time window of a visualization
        (Sprint 4.12).
        """
        now = datetime.now(timezone.utc)
        artifact = ReportArtifact(
            report_id=report.id,
            ecg_record_id=report.ecg_record_id,
            artifact_type=artifact_type.value,
            content_type=content_type,
            storage_location=storage_location,
            file_size_bytes=file_size_bytes,
            checksum_sha256=checksum_sha256,
            status=status.value,
            artifact_metadata=dict(artifact_metadata) if artifact_metadata is not None else None,
            generated_at=generated_at or now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(artifact)
        self._session.flush()
        return artifact

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, artifact_id: str) -> ReportArtifact | None:
        """Returns the artifact, or None when it does not exist."""
        return self._session.get(ReportArtifact, artifact_id)

    def require(self, artifact_id: str) -> ReportArtifact:
        """Returns the artifact, raising ``ReportArtifactNotFoundError`` when absent."""
        artifact = self.get(artifact_id)
        if artifact is None:
            raise ReportArtifactNotFoundError(f"Report artifact {artifact_id!r} does not exist")
        return artifact

    def list_for_report(
        self, report_id: str, *, artifact_type: ArtifactType | None = None
    ) -> list[ReportArtifact]:
        """Every artifact of a report version, optionally filtered by type.

        Ordered by generation time so the list reflects the order in which the
        pipeline produced the assets.
        """
        stmt = select(ReportArtifact).where(ReportArtifact.report_id == report_id)
        if artifact_type is not None:
            stmt = stmt.where(ReportArtifact.artifact_type == artifact_type.value)
        stmt = stmt.order_by(ReportArtifact.generated_at, ReportArtifact.id)
        return list(self._session.scalars(stmt))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def update_status(self, artifact: ReportArtifact, status: ArtifactStatus) -> ReportArtifact:
        """Advances the artifact's lifecycle status (Sprint 9.8).

        This is the only permitted post-registration change to an artifact.
        """
        artifact.status = status.value
        artifact.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return artifact
