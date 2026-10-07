"""Template Engine (Sprint 6.14 - 6.18).

Binds a composed ``ReportDocument`` into an approved report template and
produces the canonical HTML representation of the report.

The engine adds no content. Every displayed value comes from the document the
builders produced; where a value is unavailable the engine renders the
standardized placeholder the builders attached to it, never a sample value
(Sprint 6.16 / 3.15). It never edits the approved template's design: it
supplies data, the template supplies presentation.

The rendered document is self-contained -- the approved stylesheet and the
generated ECG figure are inlined -- so one HTML file is the complete report,
archivable and printable without external requests.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError as JinjaTemplateError
from markupsafe import Markup

from app.reporting.builders.sections import ReportDocument, ReportSection, SectionId
from app.reporting.constants import PLACEHOLDER_NOT_AVAILABLE
from app.reporting.exceptions import TemplateNotFoundError, TemplateRenderingError
from app.reporting.templates.registry import TEMPLATE_ROOT, TemplateDefinition

logger = logging.getLogger(__name__)

STYLESHEET_LOCATION = "assets/report.css"

_XML_DECLARATION = re.compile(r"^<\?xml[^>]*\?>")
_SVG_SIZE_ATTRS = re.compile(r'\s(width|height)="[^"]*"')


@dataclass(frozen=True)
class RenderedReport:
    """One rendered report document."""

    html: str
    template_id: str
    template_version: str

    def encode(self) -> bytes:
        return self.html.encode("utf-8")


def inline_svg(svg: bytes | str, *, css_class: str = "wave-svg") -> Markup:
    """Prepares a stored SVG for embedding inside the report layout.

    Strips the standalone-document XML declaration, drops the intrinsic
    width/height so the figure scales to the slot the layout gives it, and
    applies the stylesheet's figure class. The drawing itself -- geometry,
    grid, calibration and trace -- is untouched.
    """
    markup = svg.decode("utf-8") if isinstance(svg, bytes) else svg
    markup = _XML_DECLARATION.sub("", markup).strip()
    opening_end = markup.find(">")
    if not markup.startswith("<svg") or opening_end == -1:
        raise TemplateRenderingError("The stored visualization is not an SVG document")

    opening = _SVG_SIZE_ATTRS.sub("", markup[:opening_end])
    if 'class="' not in opening:
        opening = f'<svg class="{css_class}"' + opening[len("<svg") :]
    return Markup(opening + markup[opening_end:])


class TemplateEngine:
    """Renders composed report documents into the approved HTML templates."""

    def __init__(self, template_root: Path | None = None) -> None:
        self._root = template_root or TEMPLATE_ROOT
        self._environment = Environment(
            loader=FileSystemLoader(str(self._root)),
            autoescape=True,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render(
        self,
        document: ReportDocument,
        template: TemplateDefinition,
        *,
        report_id: str,
        generated_at: datetime,
        visualization_svg: bytes | None = None,
    ) -> RenderedReport:
        """Binds ``document`` into ``template`` and returns the report HTML.

        Raises:
            TemplateNotFoundError: the template file does not exist.
            TemplateRenderingError: the template could not be bound.
        """
        if not template.renders_html:
            raise TemplateNotFoundError(
                f"Template {template.template_id!r} does not render HTML"
            )
        if not template.path().is_file():
            raise TemplateNotFoundError(f"Template file {template.path()} does not exist")

        context = self._build_context(
            document,
            template,
            report_id=report_id,
            generated_at=generated_at,
            visualization_svg=visualization_svg,
        )
        try:
            html = self._environment.get_template(template.location).render(**context)
        except JinjaTemplateError as exc:
            raise TemplateRenderingError(
                f"Report {report_id!r} could not be bound to template "
                f"{template.template_id!r} v{template.version}: {exc}"
            ) from exc

        logger.info(
            "report html rendered report_id=%s template=%s version=%s bytes=%s",
            report_id,
            template.template_id,
            template.version,
            len(html.encode("utf-8")),
        )
        return RenderedReport(
            html=html, template_id=template.template_id, template_version=template.version
        )

    # ------------------------------------------------------------------
    # Binding context
    # ------------------------------------------------------------------

    def _build_context(
        self,
        document: ReportDocument,
        template: TemplateDefinition,
        *,
        report_id: str,
        generated_at: datetime,
        visualization_svg: bytes | None,
    ) -> dict:
        """The data the template binds, and nothing more.

        Sections are exposed by identifier so the template addresses each slot
        of the approved layout explicitly; a missing section resolves to an
        empty placeholder section rather than an error, so an omitted section
        degrades to a placeholder instead of failing the render.
        """
        sections = {section.id.value: section for section in document.sections}

        def section_of(section_id: str) -> ReportSection:
            existing = sections.get(section_id)
            if existing is not None:
                return existing
            return ReportSection.unavailable(
                SectionId(section_id), section_id.replace("_", " ").title(), PLACEHOLDER_NOT_AVAILABLE
            )

        def display(section_id: str, label: str) -> str:
            return section_of(section_id).display(label)

        metadata = document.metadata
        return {
            "document": document,
            "sections": sections,
            "section": section_of,
            "display": display,
            "placeholder": PLACEHOLDER_NOT_AVAILABLE,
            "stylesheet": self._stylesheet(),
            "figure_svg": inline_svg(visualization_svg) if visualization_svg else None,
            "report": {
                "id": report_id,
                "title": document.title,
                "type": document.report_type.value,
                "version": metadata.report_version,
                "ecg_record_id": metadata.ecg_record_id,
                "job_id": metadata.job_id,
                "generated_at": generated_at,
                "generated_at_display": generated_at.strftime("%d %b %Y %H:%M UTC"),
                "template_id": template.template_id,
                "template_version": template.version,
                "pipeline_version": metadata.pipeline_version,
                "schema_version": metadata.schema_version,
                "software_version": metadata.software_version,
            },
        }

    def _stylesheet(self) -> Markup:
        """The approved stylesheet, inlined verbatim so the report is self-contained."""
        path = self._root / STYLESHEET_LOCATION
        if not path.is_file():
            raise TemplateNotFoundError(f"Report stylesheet {path} does not exist")
        return Markup(path.read_text(encoding="utf-8"))
