"""Template Registry (Sprint 6.12 / 6.13).

Holds what the subsystem knows about each approved report template: its
identity, version, report type, location and supported output formats. Report
composition asks the registry for a template rather than hard-coding a layout,
so a template revision is a registry change and a version bump -- never a
change to the pipeline.

Every generated report records the template identity it was produced from, so
a historical report remains reproducible after a template is revised
(Sprint 3.18).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.reporting.constants import ReportType
from app.reporting.exceptions import TemplateNotFoundError

TEMPLATE_ROOT = Path(__file__).resolve().parent


class OutputFormat(str, Enum):
    """What a template can be rendered into."""

    HTML = "HTML"
    #: Structured report data consumed by a client that owns the presentation.
    STRUCTURED_DATA = "STRUCTURED_DATA"


@dataclass(frozen=True)
class TemplateDefinition:
    """One approved report template (Sprint 6.12)."""

    template_id: str
    name: str
    version: str
    report_type: ReportType
    supported_formats: tuple[OutputFormat, ...]
    #: Template file relative to the templates package; None when the template
    #: is not rendered by this subsystem.
    location: str | None = None

    @property
    def renders_html(self) -> bool:
        return OutputFormat.HTML in self.supported_formats and self.location is not None

    def path(self) -> Path:
        """Absolute path of the template file."""
        if self.location is None:
            raise TemplateNotFoundError(
                f"Template {self.template_id!r} has no renderable template file"
            )
        return TEMPLATE_ROOT / self.location


#: The Detailed Report template: the approved print-first clinical document.
DETAILED_REPORT_TEMPLATE = TemplateDefinition(
    template_id="ncep-detailed-report",
    name="CardioNexus Detailed Clinical Report",
    version="2.0.0",
    report_type=ReportType.DETAILED,
    supported_formats=(OutputFormat.HTML,),
    location="detailed_report.html.j2",
)

#: The Summary Report is presented by the NCEP frontend, which owns its
#: layout. The subsystem still versions the structured data contract it
#: produces for that view, so a Summary report remains reproducible and its
#: shape can evolve deliberately.
SUMMARY_REPORT_TEMPLATE = TemplateDefinition(
    template_id="ncep-summary-frontend",
    name="CardioNexus Summary Report (frontend-rendered)",
    version="1.0.0",
    report_type=ReportType.SUMMARY,
    supported_formats=(OutputFormat.STRUCTURED_DATA,),
)


class TemplateRegistry:
    """Resolves the approved template for a report type (Sprint 6.13)."""

    def __init__(self, templates: tuple[TemplateDefinition, ...] | None = None) -> None:
        self._templates = templates or (SUMMARY_REPORT_TEMPLATE, DETAILED_REPORT_TEMPLATE)

    def for_report_type(self, report_type: ReportType) -> TemplateDefinition:
        """The approved template for a report variant.

        Raises:
            TemplateNotFoundError: no template is registered for the variant.
        """
        for template in self._templates:
            if template.report_type is report_type:
                return template
        raise TemplateNotFoundError(f"No template is registered for report type {report_type.value}")

    def get(self, template_id: str) -> TemplateDefinition:
        """A specific template by identifier, for reproducing a historical report."""
        for template in self._templates:
            if template.template_id == template_id:
                return template
        raise TemplateNotFoundError(f"Template {template_id!r} is not registered")

    @property
    def templates(self) -> tuple[TemplateDefinition, ...]:
        return self._templates
