"""The artifact storage pipeline stage (Sprint 3.8 / 9.8 / 9.11).

The final stage of the pipeline. Every artifact the run produced is re-read
from the store and checked against its registry entry; only artifacts that
match advance along the lifecycle to ``AVAILABLE``, and only once every
artifact has passed does the report itself become available.

An integrity failure fails the job. A report whose documents cannot be
verified is never published, because a report that disagrees with its own
artifacts is worse than no report at all (Sprint 9.11 / 9.14).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.reporting.constants import ArtifactStatus, PipelineStage, ReportStatus, StageStatus
from app.reporting.models.generated_report import GeneratedReport
from app.reporting.orchestrator.rendering_stage import GENERATED_REPORT_OUTPUT
from app.reporting.orchestrator.stage import StageInput, StageResult
from app.reporting.repositories.artifact_repository import ReportArtifactRepository
from app.reporting.repositories.report_repository import GeneratedReportRepository
from app.reporting.storage.integrity import ArtifactIntegrityVerifier
from app.reporting.storage.lifecycle import ArtifactLifecycle

logger = logging.getLogger(__name__)


class StoreReportArtifactsStage:
    """Verifies every artifact of a report version and publishes the report."""

    stage = PipelineStage.STORE_REPORT_ARTIFACTS

    def __init__(
        self,
        session: Session,
        *,
        reports: GeneratedReportRepository | None = None,
        artifacts: ReportArtifactRepository | None = None,
        verifier: ArtifactIntegrityVerifier | None = None,
    ) -> None:
        self._session = session
        self._reports = reports or GeneratedReportRepository(session)
        self._artifacts = artifacts or ReportArtifactRepository(session)
        self._verifier = verifier or ArtifactIntegrityVerifier()

    def execute(self, payload: StageInput) -> StageResult:
        report_id = payload.outputs.get(PipelineStage.RENDER_HTML_DOCUMENTS, {}).get(
            GENERATED_REPORT_OUTPUT
        )
        if not report_id:
            return StageResult(
                status=StageStatus.FAILED,
                error_code="MissingGeneratedReport",
                error_message="Artifact storage requires a rendered report",
            )

        report = self._reports.get(report_id)
        if report is None:
            return StageResult(
                status=StageStatus.FAILED,
                error_code="GeneratedReportNotFoundError",
                error_message=f"Generated report {report_id!r} no longer exists",
            )

        artifacts = self._artifacts.list_for_report(report.id)
        if not artifacts:
            return StageResult(
                status=StageStatus.FAILED,
                error_code="ArtifactIntegrityError",
                error_message=f"Report {report.id!r} has no registered artifacts",
            )

        results = self._verifier.verify_all(report, artifacts)
        failures = [result for result in results if not result.verified]
        if failures:
            self._reports.update_status(report, ReportStatus.FAILED)
            self._session.commit()
            return StageResult(
                status=StageStatus.FAILED,
                error_code="ArtifactIntegrityError",
                error_message="; ".join(
                    f"{failure.artifact_id}: {failure.reason}" for failure in failures
                ),
            )

        for artifact in artifacts:
            self._advance(artifact, ArtifactStatus.AVAILABLE)
        self._publish(report)
        self._session.commit()

        logger.info(
            "report artifacts verified and published report_id=%s version=%s artifacts=%s",
            report.id,
            report.version,
            len(artifacts),
        )
        return StageResult(
            status=StageStatus.COMPLETED,
            artifact_ids=tuple(artifact.id for artifact in artifacts),
            messages=(
                f"{len(artifacts)} artifacts verified and released for report version "
                f"{report.version}",
            ),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _advance(self, artifact, target: ArtifactStatus) -> None:
        """Walks an artifact along its lifecycle to ``target`` (Sprint 9.8)."""
        current = ArtifactStatus(artifact.status)
        for step in ArtifactLifecycle.path(current, target):
            self._artifacts.update_status(artifact, step)

    def _publish(self, report: GeneratedReport) -> None:
        """Moves the report through storage confirmation to availability (Sprint 10.18)."""
        self._reports.update_status(report, ReportStatus.STORED)
        self._reports.update_status(report, ReportStatus.AVAILABLE)
