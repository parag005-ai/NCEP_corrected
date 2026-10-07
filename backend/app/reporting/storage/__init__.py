"""Report artifact storage package (Sprint 9.10).

Persists the bytes of generated report artifacts behind an interface that
hides the storage backend from the rest of the subsystem. The registry that
describes those artifacts lives in ``app.reporting.repositories``.
"""

from app.reporting.storage.artifact_store import ReportArtifactStore, StoredArtifact
from app.reporting.storage.integrity import ArtifactIntegrityVerifier, IntegrityResult
from app.reporting.storage.lifecycle import (
    ALLOWED_ARTIFACT_TRANSITIONS,
    LIFECYCLE_ORDER,
    ArtifactLifecycle,
)
from app.reporting.storage.reuse import ArtifactReuseService

__all__ = [
    "ALLOWED_ARTIFACT_TRANSITIONS",
    "ArtifactIntegrityVerifier",
    "ArtifactLifecycle",
    "ArtifactReuseService",
    "IntegrityResult",
    "LIFECYCLE_ORDER",
    "ReportArtifactStore",
    "StoredArtifact",
]
