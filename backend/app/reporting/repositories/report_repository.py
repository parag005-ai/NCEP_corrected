"""Persistence for Generated Reports (Sprint 2.18 / 10.8).

Database operations only, including the queries that support report
versioning and report history (Sprint 2.18: "Managing report versions",
"Retrieving report history").

A generated report is immutable (Sprint 2.24 / 3.18): this repository
deliberately exposes no way to change a report's content, lineage or
provenance after creation. Regeneration is a *new* row with the next version.
The single permitted post-creation change is the lifecycle ``status``, which
the Workflow Orchestrator advances as rendering and storage complete.

Transaction policy: methods flush, never commit; the caller owns the
transaction boundary.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.reporting.constants import (
    REPORT_PIPELINE_VERSION,
    REPORT_SCHEMA_VERSION,
    REPORTING_SOFTWARE_VERSION,
    ReportStatus,
)
from app.reporting.exceptions import GeneratedReportNotFoundError
from app.reporting.models.generated_report import GeneratedReport
from app.reporting.models.generation_job import ReportGenerationJob


class GeneratedReportRepository:
    """Creates and reads immutable, versioned ``GeneratedReport`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------------

    def next_version(self, ecg_record_id: str) -> int:
        """The next report version for a recording (1 for the first report).

        Concurrent generations for the same recording can read the same value;
        the ``(ecg_record_id, version)`` unique constraint is what ultimately
        prevents a duplicate version from being persisted.
        """
        highest = self._session.scalar(
            select(func.max(GeneratedReport.version)).where(
                GeneratedReport.ecg_record_id == ecg_record_id
            )
        )
        return (highest or 0) + 1

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        job: ReportGenerationJob,
        version: int,
        doctor_id: str | None,
        storage_dir: str,
        summary_template_id: str,
        summary_template_version: str,
        detailed_template_id: str,
        detailed_template_version: str,
        status: ReportStatus = ReportStatus.GENERATING,
        rules_version: str | None = None,
        narrative_model_version: str | None = None,
        pipeline_version: str = REPORT_PIPELINE_VERSION,
        schema_version: str = REPORT_SCHEMA_VERSION,
        software_version: str = REPORTING_SOFTWARE_VERSION,
        generated_at: datetime | None = None,
    ) -> GeneratedReport:
        """Persists the report produced by ``job``.

        Lineage is taken from the owning job rather than re-supplied by the
        caller, so a report can never disagree with the job that produced it
        about which recording, patient or organisation it belongs to.
        """
        now = datetime.now(timezone.utc)
        report = GeneratedReport(
            job_id=job.id,
            ecg_record_id=job.ecg_record_id,
            patient_id=job.patient_id,
            organisation_id=job.organisation_id,
            doctor_id=doctor_id,
            version=version,
            status=status.value,
            summary_template_id=summary_template_id,
            summary_template_version=summary_template_version,
            detailed_template_id=detailed_template_id,
            detailed_template_version=detailed_template_version,
            pipeline_version=pipeline_version,
            schema_version=schema_version,
            software_version=software_version,
            rules_version=rules_version,
            narrative_model_version=narrative_model_version,
            storage_dir=storage_dir,
            generated_at=generated_at or now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(report)
        self._session.flush()
        return report

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, report_id: str) -> GeneratedReport | None:
        """Returns the report, or None when it does not exist."""
        return self._session.get(GeneratedReport, report_id)

    def require(self, report_id: str) -> GeneratedReport:
        """Returns the report, raising ``GeneratedReportNotFoundError`` when absent."""
        report = self.get(report_id)
        if report is None:
            raise GeneratedReportNotFoundError(f"Generated report {report_id!r} does not exist")
        return report

    def get_by_job(self, job_id: str) -> GeneratedReport | None:
        """The report produced by one generation job, if it reached creation."""
        return self._session.scalar(select(GeneratedReport).where(GeneratedReport.job_id == job_id))

    def get_version(self, ecg_record_id: str, version: int) -> GeneratedReport | None:
        """One specific historical version of a recording's report."""
        return self._session.scalar(
            select(GeneratedReport).where(
                GeneratedReport.ecg_record_id == ecg_record_id,
                GeneratedReport.version == version,
            )
        )

    def get_latest_for_ecg_record(self, ecg_record_id: str) -> GeneratedReport | None:
        """The highest existing report version for a recording."""
        return self._session.scalar(
            select(GeneratedReport)
            .where(GeneratedReport.ecg_record_id == ecg_record_id)
            .order_by(GeneratedReport.version.desc())
            .limit(1)
        )

    def list_for_ecg_record(
        self, ecg_record_id: str, *, limit: int = 50, offset: int = 0
    ) -> list[GeneratedReport]:
        """Report history for one recording, newest version first."""
        stmt = (
            select(GeneratedReport)
            .where(GeneratedReport.ecg_record_id == ecg_record_id)
            .order_by(GeneratedReport.version.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.scalars(stmt))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def update_status(self, report: GeneratedReport, status: ReportStatus) -> GeneratedReport:
        """Advances the report's lifecycle status (Sprint 10.18).

        This is the only permitted post-creation change to a generated report.
        """
        report.status = status.value
        report.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return report
