"""Rollback of a failed report generation (Sprint 3.14 / 9.14).

A report generation either completes or leaves nothing behind. Stages persist
as they go -- the report version is created before it is rendered, documents
are stored before they are registered -- so a failure part-way through would
otherwise strand a report row that was never published, registry entries
pointing at an incomplete set of documents, and files on disk that no report
will ever reference.

This component removes that partial output when the Workflow Orchestrator
fails or cancels a job, restoring the clean state the run started from.
Deleting the report version cascades to its registered artifacts; the job's
directory in the artifact store is removed with it.

Cleanup is best effort and never masks the failure that triggered it: if the
rollback itself fails it is logged and the job is still recorded as failed.
"""

from __future__ import annotations

import logging
from typing import Protocol

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.reporting.models.generation_job import ReportGenerationJob
from app.reporting.models.report_artifact import ReportArtifact
from app.reporting.repositories.report_repository import GeneratedReportRepository
from app.reporting.storage.artifact_store import ReportArtifactStore

logger = logging.getLogger(__name__)


class JobFailureCleanup(Protocol):
    """Removes whatever a failed report generation left behind."""

    def clean(self, job: ReportGenerationJob) -> None:
        """Rolls back the partial output of ``job``. Must not raise."""


class ReportGenerationCleanup:
    """Deletes the partial report version and documents of a failed job."""

    def __init__(
        self,
        session: Session,
        store: ReportArtifactStore,
        *,
        reports: GeneratedReportRepository | None = None,
    ) -> None:
        self._session = session
        self._store = store
        self._reports = reports or GeneratedReportRepository(session)

    def clean(self, job: ReportGenerationJob) -> None:
        """Removes the report version this job created, and its stored documents."""
        try:
            self._delete_report(job)
            self._delete_documents(job)
        except Exception:  # noqa: BLE001 -- rollback must never mask the original failure
            logger.exception("failed to roll back the partial output of job %s", job.id)
            self._session.rollback()

    def _delete_report(self, job: ReportGenerationJob) -> None:
        """Deletes the unpublished report version and its registry entries.

        The artifacts are removed explicitly rather than left to the database's
        cascade: SQLite does not enforce foreign keys unless asked to, and a
        rollback that silently left registry rows behind on one backend but not
        another would be worse than no rollback at all.
        """
        report = self._reports.get_by_job(job.id)
        if report is None:
            return
        logger.info(
            "rolling back partial report report_id=%s version=%s job_id=%s",
            report.id,
            report.version,
            job.id,
        )
        self._session.execute(
            delete(ReportArtifact).where(ReportArtifact.report_id == report.id)
        )
        self._session.delete(report)
        self._session.commit()

    def _delete_documents(self, job: ReportGenerationJob) -> None:
        """Removes every document this job stored, including its Cloudinary backup."""
        self._store.remove_job(job.ecg_record_id, job.id)
        logger.info("removed partial report documents job_id=%s", job.id)
