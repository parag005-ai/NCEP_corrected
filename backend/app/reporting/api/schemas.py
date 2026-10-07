"""Request and response schemas for the Report Generation API (Sprint 10.15).

Responses use the platform's camelCase convention (``CamelModel``) so the
frontend consumes them exactly like every other NCEP resource.

Nothing here exposes an internal location. A caller receives artifact
identifiers and the URLs to fetch them by; the storage directory, the relative
path inside it and the absolute path on disk stay on the server (Sprint 10.24).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas import CamelModel

#: Mounted path of the Report Generation API, used to build navigational URLs.
API_PREFIX = "/api/report-generation"


class ReportGenerationRequest(CamelModel):
    """What a client may ask for: a report, for one recording.

    Tenant, patient, doctor and organisation are resolved from the recording
    and the authenticated session -- a client cannot supply them.
    """

    ecg_record_id: str = Field(min_length=1)


class ReportArtifactOut(CamelModel):
    """One registered document of a generated report."""

    id: str
    artifact_type: str
    content_type: str
    file_size_bytes: int
    checksum_sha256: str
    status: str
    generated_at: datetime
    artifact_metadata: dict | None = None
    download_url: str


class GeneratedReportOut(CamelModel):
    """A generated report version and the documents it produced."""

    id: str
    job_id: str
    ecg_record_id: str
    patient_id: str
    doctor_id: str | None = None
    version: int
    status: str
    generated_at: datetime
    summary_template_id: str
    summary_template_version: str
    detailed_template_id: str
    detailed_template_version: str
    pipeline_version: str
    schema_version: str
    software_version: str
    artifacts: list[ReportArtifactOut] = Field(default_factory=list)
    html_url: str | None = None
    pdf_url: str | None = None
    #: Where the Summary Report's structured data is served from.
    summary_url: str | None = None


class ReportGenerationJobOut(CamelModel):
    """The state of one report generation, and where to go next.

    ``errorMessage`` is a safe summary derived from the failure category; the
    underlying diagnostic text stays in the job record for operators.
    """

    id: str
    ecg_record_id: str
    status: str
    progress_percent: int
    current_stage: str | None = None
    failed_stage: str | None = None
    attempt_count: int
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    report_id: str | None = None
    status_url: str
    report_url: str | None = None
