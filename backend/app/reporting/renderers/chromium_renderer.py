"""Chromium-backed PDF renderer (Sprint 9.5).

Renders the report HTML with the same engine a clinician views it in, which is
what makes the PDF and the HTML representations of a report version agree
(approved decision: HTML and PDF for one report version must remain
consistent). The approved stylesheet is built on CSS grid and ``@page``; a
print-only CSS engine renders that layout differently, so the browser engine
is the choice that preserves the approved design.

The renderer is given finished, self-contained HTML -- the stylesheet and the
ECG figure are already inlined -- so it loads no external resource and needs no
network access.
"""

from __future__ import annotations

import logging

from app.reporting.exceptions import PDFRenderingError

logger = logging.getLogger(__name__)

#: Page geometry comes from the stylesheet's own ``@page`` rule; margins are
#: zero because the approved page composition owns its own padding.
PAGE_MARGIN = {"top": "0", "bottom": "0", "left": "0", "right": "0"}

DEFAULT_TIMEOUT_MS = 30_000


class ChromiumPDFRenderer:
    """Renders report HTML to PDF using a headless Chromium instance."""

    engine = "chromium"

    def __init__(self, *, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> None:
        self._timeout_ms = timeout_ms
        self._engine_version = "unknown"

    @property
    def engine_version(self) -> str:
        """The browser build that rendered the most recent document."""
        return self._engine_version

    def render(self, html: str) -> bytes:
        """Renders a complete HTML document into PDF bytes.

        Background graphics are printed and the stylesheet's page size is
        honoured, so the PDF reproduces the approved page composition rather
        than a browser default.

        Raises:
            PDFRenderingError: the rendering engine is unavailable or failed.
        """
        try:
            from playwright.sync_api import Error as PlaywrightError, sync_playwright
        except ImportError as exc:  # pragma: no cover - exercised by deployment, not tests
            raise PDFRenderingError(
                "The Chromium rendering engine is not installed; run 'playwright install chromium'"
            ) from exc

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    self._engine_version = browser.version
                    page = browser.new_page()
                    page.set_content(html, wait_until="load", timeout=self._timeout_ms)
                    pdf = page.pdf(
                        format="A4",
                        prefer_css_page_size=True,
                        print_background=True,
                        margin=PAGE_MARGIN,
                    )
                finally:
                    browser.close()
        except PlaywrightError as exc:
            raise PDFRenderingError(f"Chromium could not render the report document: {exc}") from exc

        logger.info(
            "report pdf rendered engine=%s version=%s bytes=%s",
            self.engine,
            self._engine_version,
            len(pdf),
        )
        return pdf
