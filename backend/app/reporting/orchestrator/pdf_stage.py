"""The PDF generation pipeline stage (Sprint 3.8 / 9.4).

Converts the report's canonical HTML into a downloadable PDF:

    read back the registered HTML artifact
    -> verify it still matches the registry
    -> render it
    -> store and register the PDF against the same report version

The stage never composes or re-binds report content: it renders the exact
bytes that were registered as the report's HTML, and records that document's
checksum on the PDF. A PDF can therefore always be traced to -- and checked
against -- the HTML it was produced from, which is what keeps the two
representations of a report version consistent.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.reporting.constants import ArtifactStatus, ArtifactType, PipelineStage, ReportType, StageStatus
from app.reporting.exceptions import ArtifactIntegrityError, PDFRenderingError
from app.reporting.models.generated_report import GeneratedReport
from app.reporting.models.report_artifact import ReportArtifact
from app.reporting.orchestrator.rendering_stage import GENERATED_REPORT_OUTPUT
from app.reporting.orchestrator.stage import StageInput, StageResult
from app.reporting.renderers.pdf_renderer import PDF_CONTENT_TYPE, PDF_MAGIC, PDFRenderer
from app.reporting.repositories.artifact_repository import ReportArtifactRepository
from app.reporting.repositories.report_repository import GeneratedReportRepository
from app.reporting.storage.artifact_store import ReportArtifactStore
from app.reporting.storage.integrity import ArtifactIntegrityVerifier

logger = logging.getLogger(__name__)

DETAILED_PDF_LOCATION = "documents/detailed_report.pdf"


class GeneratePDFDocumentsStage:
    """Renders the report's PDF from its already-generated HTML."""

    stage = PipelineStage.GENERATE_PDF_DOCUMENTS

    def __init__(
        self,
        session: Session,
        store: ReportArtifactStore,
        renderer: PDFRenderer,
        *,
        reports: GeneratedReportRepository | None = None,
        artifacts: ReportArtifactRepository | None = None,
        verifier: ArtifactIntegrityVerifier | None = None,
    ) -> None:
        self._session = session
        self._store = store
        self._renderer = renderer
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
                error_message="PDF generation requires a rendered report",
            )

        report = self._reports.get(report_id)
        if report is None:
            return StageResult(
                status=StageStatus.FAILED,
                error_code="GeneratedReportNotFoundError",
                error_message=f"Generated report {report_id!r} no longer exists",
            )

        try:
            source, html = self._verified_source_html(report)
            pdf = self._renderer.render(html)
            self._verify_output(pdf)
        except (ArtifactIntegrityError, PDFRenderingError) as exc:
            return StageResult(
                status=StageStatus.FAILED,
                error_code=type(exc).__name__,
                error_message=str(exc),
            )

        stored = self._store.write(
            ecg_record_id=report.ecg_record_id,
            job_id=payload.job.id,
            relative_path=DETAILED_PDF_LOCATION,
            data=pdf,
        )
        artifact = self._artifacts.register(
            report=report,
            artifact_type=ArtifactType.DETAILED_PDF,
            content_type=PDF_CONTENT_TYPE,
            storage_location=stored.relative_path,
            file_size_bytes=stored.file_size_bytes,
            checksum_sha256=stored.checksum_sha256,
            status=ArtifactStatus.REGISTERED,
            artifact_metadata={
                "report_type": ReportType.DETAILED.value,
                "template_id": report.detailed_template_id,
                "template_version": report.detailed_template_version,
                # The document this PDF was rendered from, and the bytes it saw.
                "source_artifact_id": source.id,
                "source_checksum_sha256": source.checksum_sha256,
                "rendering_engine": self._renderer.engine,
                "rendering_engine_version": self._renderer.engine_version,
            },
        )
        self._session.commit()

        logger.info(
            "report pdf generated report_id=%s artifact_id=%s bytes=%s",
            report.id,
            artifact.id,
            stored.file_size_bytes,
        )
        return StageResult(
            status=StageStatus.COMPLETED,
            artifact_ids=(artifact.id,),
            messages=(
                f"Detailed PDF rendered from the registered HTML "
                f"({stored.file_size_bytes} bytes, {self._renderer.engine})",
            ),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _verified_source_html(self, report: GeneratedReport) -> tuple[ReportArtifact, str]:
        """The registered HTML of this report version, verified before use.

        Rendering an HTML document that no longer matches its registry entry
        would produce a PDF that disagrees with the report it claims to be.
        """
        candidates = self._artifacts.list_for_report(
            report.id, artifact_type=ArtifactType.DETAILED_HTML
        )
        if not candidates:
            raise ArtifactIntegrityError(
                f"Report {report.id!r} has no registered HTML document to render"
            )

        source = candidates[-1]
        result = self._verifier.verify(report, source)
        if not result.verified:
            raise ArtifactIntegrityError(
                f"Report {report.id!r} HTML document failed verification: {result.reason}"
            )
        return source, self._store.read(self._verifier.resolve(report, source)).decode("utf-8")

    @staticmethod
    def _verify_output(pdf: bytes) -> None:
        """Confirms the renderer actually produced a PDF (Sprint 9.11)."""
        if not pdf.startswith(PDF_MAGIC):
            raise PDFRenderingError("The rendering engine did not return a PDF document")
