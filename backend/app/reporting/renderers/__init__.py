"""Document renderer package (Sprint 9.3 - 9.5).

Converts generated report HTML into downloadable documents. Renderers receive
finished HTML and return bytes; they never compose or regenerate report
content, so a rendered document always agrees with the HTML it came from.
"""

from app.reporting.renderers.chromium_renderer import ChromiumPDFRenderer
from app.reporting.renderers.pdf_renderer import PDF_CONTENT_TYPE, PDF_MAGIC, PDFRenderer

__all__ = ["PDF_CONTENT_TYPE", "PDF_MAGIC", "ChromiumPDFRenderer", "PDFRenderer"]
