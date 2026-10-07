"""Template package (Sprint 6.11 - 6.18).

Holds the approved report templates, the registry that resolves them, and the
Template Engine that binds composed report documents into them.

Templates define presentation only: they contain no business logic and no
clinical calculation, and the engine never modifies their design.
"""

from app.reporting.templates.engine import (
    STYLESHEET_LOCATION,
    RenderedReport,
    TemplateEngine,
    inline_svg,
)
from app.reporting.templates.registry import (
    DETAILED_REPORT_TEMPLATE,
    SUMMARY_REPORT_TEMPLATE,
    TEMPLATE_ROOT,
    OutputFormat,
    TemplateDefinition,
    TemplateRegistry,
)

__all__ = [
    "DETAILED_REPORT_TEMPLATE",
    "OutputFormat",
    "RenderedReport",
    "STYLESHEET_LOCATION",
    "SUMMARY_REPORT_TEMPLATE",
    "TEMPLATE_ROOT",
    "TemplateDefinition",
    "TemplateEngine",
    "TemplateRegistry",
    "inline_svg",
]
