"""A generated artifact that has been stored but not yet registered.

A pipeline stage writes its output (an SVG today, HTML and PDF later) as soon
as it produces it, but the ``GeneratedReport`` row that will own the registry
entry is created by the report composition stage, which runs afterwards. This
descriptor carries everything the registry needs -- location, size, checksum,
generation time and the artifact-specific metadata Sprint 4.12 requires --
from the stage that produced the file to the stage that registers it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.reporting.constants import ArtifactType
from app.reporting.models.documents import freeze_document


@dataclass(frozen=True)
class PendingReportArtifact:
    """A stored artifact awaiting registration against a report version."""

    artifact_type: ArtifactType
    content_type: str
    storage_location: str
    absolute_path: str
    file_size_bytes: int
    checksum_sha256: str
    generated_at: datetime
    #: Artifact-specific facts the registry preserves, e.g. the lead and time
    #: window a visualization shows (Sprint 4.12).
    artifact_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_metadata", freeze_document(dict(self.artifact_metadata)))
