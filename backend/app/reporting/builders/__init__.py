"""Report composition package (Sprint 6).

Transforms the immutable Generation Context into structured report documents:
sections, labelled values and figure references. Both report variants are
built from the same context and the same section builders, so they can never
state different facts.

Nothing in this package produces markup. Turning a built document into HTML is
the Template Engine's sole responsibility (Sprint 6.15 / 6.17).
"""

from app.reporting.builders.report_builders import DetailedReportBuilder, SummaryReportBuilder
from app.reporting.builders.sections import (
    Availability,
    ReportDocument,
    ReportDocumentMetadata,
    ReportFigure,
    ReportSection,
    ReportValue,
    SectionId,
)

__all__ = [
    "Availability",
    "DetailedReportBuilder",
    "ReportDocument",
    "ReportDocumentMetadata",
    "ReportFigure",
    "ReportSection",
    "ReportValue",
    "SectionId",
    "SummaryReportBuilder",
]
