"""The Document Renderer contract (Sprint 9.3 / 9.5).

A renderer converts an already-generated report HTML document into a
downloadable document. It receives finished HTML and returns bytes: it never
composes a report, never binds data and never regenerates content, so the PDF
can only ever be a faithful rendition of the HTML that produced it (approved
decision: PDF generation consumes the generated HTML).

The contract is a ``Protocol`` so the rendering backend can be replaced --
a different browser engine, a print service, a future export format -- without
the pipeline knowing (Sprint 9.10 / 9.15).
"""

from __future__ import annotations

from typing import Protocol

PDF_CONTENT_TYPE = "application/pdf"

#: Every PDF document begins with this signature.
PDF_MAGIC = b"%PDF-"


class PDFRenderer(Protocol):
    """Converts a complete HTML document into PDF bytes."""

    @property
    def engine(self) -> str:
        """Identifier of the rendering engine, recorded in artifact metadata."""

    @property
    def engine_version(self) -> str:
        """Version of the rendering engine, recorded for reproducibility."""

    def render(self, html: str) -> bytes:
        """Renders one self-contained HTML document into PDF bytes.

        Raises:
            PDFRenderingError: the document could not be rendered.
        """
