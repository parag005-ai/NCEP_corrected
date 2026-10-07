"""Report Generation API package (Sprint 10).

Exposes the already-implemented generation pipeline over HTTP: request a
report, poll its progress, list versions, and download the documents it
produced. The layer holds no business logic -- it authorizes, delegates to the
Workflow Orchestrator or a repository, and shapes the response.
"""

from app.reporting.api.routes import router

__all__ = ["router"]
