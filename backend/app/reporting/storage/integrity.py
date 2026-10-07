"""Artifact integrity verification (Sprint 9.11).

Before an artifact is made available, the bytes on disk are re-read and
checked against what the registry recorded when it was produced: the file
exists, its size matches, and its SHA-256 checksum matches. Only artifacts
that pass are released to downstream consumers.

The verifier compares the *stored* file against the *registry*; it never
repairs, rewrites or re-registers anything. A mismatch means the artifact and
its registry entry disagree, which is a failure to report, not to fix.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from app.reporting.models.generated_report import GeneratedReport
from app.reporting.models.report_artifact import ReportArtifact

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntegrityResult:
    """The outcome of verifying one stored artifact."""

    artifact_id: str
    verified: bool
    reason: str | None = None

    @classmethod
    def passed(cls, artifact_id: str) -> "IntegrityResult":
        return cls(artifact_id=artifact_id, verified=True)

    @classmethod
    def failed(cls, artifact_id: str, reason: str) -> "IntegrityResult":
        return cls(artifact_id=artifact_id, verified=False, reason=reason)


class ArtifactIntegrityVerifier:
    """Re-verifies stored artifacts against their registry entries."""

    def resolve(self, report: GeneratedReport, artifact: ReportArtifact) -> Path:
        """Where an artifact's bytes live: its location within the report's directory."""
        return Path(report.storage_dir) / artifact.storage_location

    def verify(self, report: GeneratedReport, artifact: ReportArtifact) -> IntegrityResult:
        """Checks that the stored file is present and matches the registry."""
        path = self.resolve(report, artifact)
        if not path.is_file():
            return IntegrityResult.failed(artifact.id, f"stored artifact is missing at {path}")

        data = path.read_bytes()
        if len(data) != artifact.file_size_bytes:
            return IntegrityResult.failed(
                artifact.id,
                f"stored artifact is {len(data)} bytes but the registry records "
                f"{artifact.file_size_bytes}",
            )

        checksum = hashlib.sha256(data).hexdigest()
        if checksum != artifact.checksum_sha256:
            return IntegrityResult.failed(
                artifact.id, "stored artifact does not match its recorded checksum"
            )

        return IntegrityResult.passed(artifact.id)

    def verify_all(
        self, report: GeneratedReport, artifacts: list[ReportArtifact]
    ) -> tuple[IntegrityResult, ...]:
        """Verifies every artifact of a report version."""
        results = tuple(self.verify(report, artifact) for artifact in artifacts)
        failures = [result for result in results if not result.verified]
        if failures:
            logger.error(
                "artifact integrity failed report_id=%s failures=%s",
                report.id,
                [f"{result.artifact_id}: {result.reason}" for result in failures],
            )
        return results
