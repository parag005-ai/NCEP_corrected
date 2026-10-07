"""SourceInformation domain object.

Carries the traceability information Business Rule 8.17 ("Preserve Data
Lineage") requires: every standardized ECGRecord must retain enough
information to identify the uploaded recording it originated from, without
leaking format-specific structures beyond the ingestion boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.ecg.constants import ECGFormat


@dataclass(frozen=True)
class SourceInformation:
    """Lineage metadata linking an ECGRecord back to its uploaded source files."""

    upload_id: str
    source_format: ECGFormat
    original_filenames: tuple[str, ...] = field(default_factory=tuple)
    parser_name: str = ""
    ingested_at: datetime | None = None
