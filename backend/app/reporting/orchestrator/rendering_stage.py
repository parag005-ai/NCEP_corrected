"""The HTML rendering pipeline stage (Sprint 3.8 / 6.17 / 6.19 / 6.20).

This is where a report first becomes a persisted, versioned thing:

    resolve the approved templates for both variants
    -> create the GeneratedReport row, whose template identity is now known
    -> bind the composed Detailed document into its template
    -> store the rendered HTML
    -> register it, and every artifact that was pending, against the report

Artifact registration happens here and not earlier because the registry entry
belongs to a report version, and the report version does not exist until this
point (approved artifact lifecycle: artifacts may be stored as soon as they
are produced, but stay pending until a GeneratedReport exists).

The Summary report is presented by the NCEP frontend, which owns its layout,
so no Summary HTML or PDF is rendered. Its composed document is persisted
here as structured data instead, beside the Detailed HTML and under the same
report version.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.reporting.builders.sections import ReportDocument
from app.reporting.builders.serialization import SUMMARY_CONTRACT_VERSION, document_to_dict
from app.reporting.constants import ArtifactStatus, ArtifactType, PipelineStage, ReportStatus, ReportType, StageStatus
from app.reporting.exceptions import TemplateError
from app.reporting.models.generated_report import GeneratedReport
from app.reporting.models.pending_artifact import PendingReportArtifact
from app.reporting.orchestrator.composition_stages import (
    DETAILED_DOCUMENT_OUTPUT,
    SUMMARY_DOCUMENT_OUTPUT,
)
from app.reporting.orchestrator.stage import StageInput, StageResult
from app.reporting.orchestrator.visualization_stage import RAW_ECG_ARTIFACT_OUTPUT
from app.reporting.repositories.artifact_repository import ReportArtifactRepository
from app.reporting.repositories.report_repository import GeneratedReportRepository
from app.reporting.storage.artifact_store import ReportArtifactStore
from app.reporting.templates.engine import TemplateEngine
from app.reporting.templates.registry import TemplateRegistry

logger = logging.getLogger(__name__)

#: Key under which the persisted report is published to later stages.
GENERATED_REPORT_OUTPUT = "generated_report_id"

DETAILED_HTML_LOCATION = "documents/detailed_report.html"
SUMMARY_JSON_LOCATION = "documents/summary_report.json"
HTML_CONTENT_TYPE = "text/html; charset=utf-8"
JSON_CONTENT_TYPE = "application/json; charset=utf-8"


class RenderHTMLDocumentsStage:
    """Creates the report version and renders its canonical HTML."""

    stage = PipelineStage.RENDER_HTML_DOCUMENTS

    def __init__(
        self,
        session: Session,
        store: ReportArtifactStore,
        *,
        registry: TemplateRegistry | None = None,
        engine: TemplateEngine | None = None,
        reports: GeneratedReportRepository | None = None,
        artifacts: ReportArtifactRepository | None = None,
    ) -> None:
        self._session = session
        self._store = store
        self._registry = registry or TemplateRegistry()
        self._engine = engine or TemplateEngine()
        self._reports = reports or GeneratedReportRepository(session)
        self._artifacts = artifacts or ReportArtifactRepository(session)

    def execute(self, payload: StageInput) -> StageResult:
        context = payload.context
        if context is None:
            return StageResult(
                status=StageStatus.FAILED,
                error_code="MissingGenerationContext",
                error_message="Rendering requires a loaded generation context",
            )

        detailed = self._document(payload, PipelineStage.BUILD_DETAILED_REPORT, DETAILED_DOCUMENT_OUTPUT)
        summary = self._document(payload, PipelineStage.BUILD_SUMMARY_REPORT, SUMMARY_DOCUMENT_OUTPUT)
        if detailed is None or summary is None:
            return StageResult(
                status=StageStatus.FAILED,
                error_code="MissingReportDocument",
                error_message="Rendering requires both composed report documents",
            )

        try:
            report = self._create_report(payload, detailed)
            rendered = self._engine.render(
                detailed,
                self._registry.for_report_type(ReportType.DETAILED),
                report_id=report.id,
                generated_at=detailed.metadata.generated_at,
                visualization_svg=self._visualization_svg(payload),
            )
        except TemplateError as exc:
            return StageResult(
                status=StageStatus.FAILED,
                error_code=type(exc).__name__,
                error_message=str(exc),
            )

        stored = self._store.write(
            ecg_record_id=report.ecg_record_id,
            job_id=payload.job.id,
            relative_path=DETAILED_HTML_LOCATION,
            data=rendered.encode(),
        )
        stored_summary = self._store_summary(payload, report, summary)
        artifact_ids = self._register_artifacts(payload, report, stored, stored_summary)
        self._reports.update_status(report, ReportStatus.RENDERED)
        self._session.commit()

        logger.info(
            "report rendered report_id=%s version=%s artifacts=%s",
            report.id,
            report.version,
            len(artifact_ids),
        )
        return StageResult(
            status=StageStatus.COMPLETED,
            outputs={GENERATED_REPORT_OUTPUT: report.id},
            artifact_ids=artifact_ids,
            messages=(
                f"Detailed report rendered from {rendered.template_id} v{rendered.template_version} "
                f"({stored.file_size_bytes} bytes)",
            ),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _document(payload: StageInput, stage: PipelineStage, key: str) -> ReportDocument | None:
        return payload.outputs.get(stage, {}).get(key)

    @staticmethod
    def _pending_visualization(payload: StageInput) -> PendingReportArtifact | None:
        return payload.outputs.get(PipelineStage.GENERATE_VISUALIZATIONS, {}).get(
            RAW_ECG_ARTIFACT_OUTPUT
        )

    def _visualization_svg(self, payload: StageInput) -> bytes | None:
        """The stored ECG figure, read back for embedding in the report."""
        pending = self._pending_visualization(payload)
        if pending is None:
            return None
        return Path(pending.absolute_path).read_bytes()

    def _create_report(self, payload: StageInput, document: ReportDocument) -> GeneratedReport:
        """Persists the report version this render produces (Sprint 3.18)."""
        summary_template = self._registry.for_report_type(ReportType.SUMMARY)
        detailed_template = self._registry.for_report_type(ReportType.DETAILED)
        context = payload.context
        return self._reports.create(
            job=payload.job,
            version=document.metadata.report_version,
            doctor_id=context.doctor.doctor_id if context.doctor else None,
            storage_dir=str(self._store.job_dir(payload.job.ecg_record_id, payload.job.id)),
            summary_template_id=summary_template.template_id,
            summary_template_version=summary_template.version,
            detailed_template_id=detailed_template.template_id,
            detailed_template_version=detailed_template.version,
            status=ReportStatus.GENERATING,
            generated_at=document.metadata.generated_at,
        )

    def _store_summary(self, payload: StageInput, report: GeneratedReport, summary: ReportDocument):
        """Writes the composed Summary Report as structured data.

        The Summary's presentation belongs to the frontend, so it is delivered
        as its delivery contract rather than as a rendered document. It is
        written here, beside the Detailed HTML and from the same generation, so
        the two can only ever describe the same report version and are rolled
        back together if the run does not finish.
        """
        return self._store.write(
            ecg_record_id=report.ecg_record_id,
            job_id=payload.job.id,
            relative_path=SUMMARY_JSON_LOCATION,
            data=json.dumps(
                document_to_dict(summary, report_id=report.id), indent=2, sort_keys=False
            ).encode("utf-8"),
        )

    def _register_artifacts(
        self, payload: StageInput, report: GeneratedReport, stored, stored_summary
    ) -> tuple[str, ...]:
        """Registers the rendered documents and every artifact still pending (Sprint 6.20)."""
        registered = [
            self._artifacts.register(
                report=report,
                artifact_type=ArtifactType.DETAILED_HTML,
                content_type=HTML_CONTENT_TYPE,
                storage_location=stored.relative_path,
                file_size_bytes=stored.file_size_bytes,
                checksum_sha256=stored.checksum_sha256,
                status=ArtifactStatus.REGISTERED,
                artifact_metadata={
                    "report_type": ReportType.DETAILED.value,
                    "template_id": report.detailed_template_id,
                    "template_version": report.detailed_template_version,
                },
            ).id,
            self._artifacts.register(
                report=report,
                artifact_type=ArtifactType.SUMMARY_JSON,
                content_type=JSON_CONTENT_TYPE,
                storage_location=stored_summary.relative_path,
                file_size_bytes=stored_summary.file_size_bytes,
                checksum_sha256=stored_summary.checksum_sha256,
                status=ArtifactStatus.REGISTERED,
                artifact_metadata={
                    "report_type": ReportType.SUMMARY.value,
                    "template_id": report.summary_template_id,
                    "template_version": report.summary_template_version,
                    "contract_version": SUMMARY_CONTRACT_VERSION,
                },
            ).id,
        ]

        pending = self._pending_visualization(payload)
        if pending is not None:
            registered.append(
                self._artifacts.register(
                    report=report,
                    artifact_type=pending.artifact_type,
                    content_type=pending.content_type,
                    storage_location=pending.storage_location,
                    file_size_bytes=pending.file_size_bytes,
                    checksum_sha256=pending.checksum_sha256,
                    status=ArtifactStatus.REGISTERED,
                    generated_at=pending.generated_at,
                    artifact_metadata=dict(pending.artifact_metadata),
                ).id
            )
        return tuple(registered)
