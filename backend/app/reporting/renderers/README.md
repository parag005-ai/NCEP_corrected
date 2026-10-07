## Reporting Renderers

Responsibility: Convert an already-generated report HTML document into downloadable documents (Phase 1: PDF).
Inputs: The finished, self-contained HTML of one report version, read back from the artifact store.
Outputs: Document bytes, plus the rendering engine and version recorded for reproducibility.
Dependencies: `app.reporting.exceptions`, Playwright/Chromium.

Renderers never compose, bind or regenerate report content — a rendered document can only be a faithful rendition of the HTML it was given, which is what keeps the HTML and PDF of one report version consistent.

Chromium is the backend because the approved stylesheet is built on CSS grid and `@page`; a print-only CSS engine renders that layout differently. `PDFRenderer` is a Protocol, so the backend can be replaced without the pipeline knowing.

**Deployment note:** the browser binary is not installed by `pip`. Run `playwright install chromium` on any host that generates reports.
