"""Artifact reuse across report versions (Sprint 4.21 / 9.6).

Regenerating a report for an unchanged recording should not redo work whose
output cannot differ. The ECG visualization is deterministic and the recording
it is drawn from is immutable, so a strip already produced for that recording
under the same rendering policy is reused instead of being drawn again.

Reuse is deliberately conservative. It applies only when the recording, the
artifact type and the rendering policy version all match a previously
registered artifact whose bytes are still present. The carried-over bytes are
re-measured after copying, so the new report version's registry entry always
describes the file that actually exists beside it rather than inheriting a
checksum on trust.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.reporting.constants import ArtifactStatus, ArtifactType
from app.reporting.exceptions import ReportArtifactStorageError
from app.reporting.models.generated_report import GeneratedReport
from app.reporting.models.pending_artifact import PendingReportArtifact
from app.reporting.models.report_artifact import ReportArtifact
from app.reporting.storage.artifact_store import ReportArtifactStore

logger = logging.getLogger(__name__)

#: Statuses whose artifacts are complete enough to be carried over.
REUSABLE_STATUSES = frozenset(
    {
        ArtifactStatus.REGISTERED.value,
        ArtifactStatus.VALIDATED.value,
        ArtifactStatus.STORED.value,
        ArtifactStatus.AVAILABLE.value,
    }
)


class ArtifactReuseService:
    """Finds and carries over artifacts that a new report version can reuse."""

    def __init__(self, session: Session, store: ReportArtifactStore) -> None:
        self._session = session
        self._store = store

    def find_reusable(
        self,
        *,
        ecg_record_id: str,
        artifact_type: ArtifactType,
        policy_version: str,
        job_id: str,
    ) -> PendingReportArtifact | None:
        """Carries over a matching artifact, or returns None when there is none.

        Returns a pending artifact describing the copy made for this job, ready
        to be registered against the report version this run produces.
        """
        candidate = self._latest_candidate(ecg_record_id, artifact_type, policy_version)
        if candidate is None:
            return None

        artifact, report = candidate
        source = Path(report.storage_dir) / artifact.storage_location
        if not source.is_file():
            logger.info(
                "artifact not reused, source is gone artifact_id=%s path=%s", artifact.id, source
            )
            return None

        try:
            stored = self._store.copy(
                source_path=source,
                ecg_record_id=ecg_record_id,
                job_id=job_id,
                relative_path=artifact.storage_location,
            )
        except ReportArtifactStorageError:
            logger.warning("artifact could not be reused artifact_id=%s", artifact.id, exc_info=True)
            return None

        if stored.checksum_sha256 != artifact.checksum_sha256:
            logger.warning(
                "artifact not reused, copy does not match source artifact_id=%s", artifact.id
            )
            return None

        logger.info(
            "artifact reused ecg_record_id=%s type=%s source_artifact_id=%s",
            ecg_record_id,
            artifact_type.value,
            artifact.id,
        )
        metadata = dict(artifact.artifact_metadata or {})
        metadata["reused_from_artifact_id"] = artifact.id
        return PendingReportArtifact(
            artifact_type=artifact_type,
            content_type=artifact.content_type,
            storage_location=stored.relative_path,
            absolute_path=stored.absolute_path,
            file_size_bytes=stored.file_size_bytes,
            checksum_sha256=stored.checksum_sha256,
            generated_at=artifact.generated_at,
            artifact_metadata=metadata,
        )

    def _latest_candidate(
        self, ecg_record_id: str, artifact_type: ArtifactType, policy_version: str
    ) -> tuple[ReportArtifact, GeneratedReport] | None:
        """The most recent registered artifact eligible for reuse."""
        rows = self._session.execute(
            select(ReportArtifact, GeneratedReport)
            .join(GeneratedReport, ReportArtifact.report_id == GeneratedReport.id)
            .where(
                ReportArtifact.ecg_record_id == ecg_record_id,
                ReportArtifact.artifact_type == artifact_type.value,
                ReportArtifact.status.in_(REUSABLE_STATUSES),
            )
            .order_by(GeneratedReport.version.desc())
        ).all()

        for artifact, report in rows:
            metadata = artifact.artifact_metadata or {}
            if metadata.get("policy_version") == policy_version:
                return artifact, report
        return None
