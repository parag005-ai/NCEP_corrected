"""Annotation domain objects.

Represents labels or events already present in the source ECG
(Implementation Spec 4.7 / 5.7). Phase 1 preserves existing annotations; it
never generates new ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.ecg.constants import CanonicalLead


class AnnotationType(str, Enum):
    """Category of a preserved source annotation."""

    BEAT = "beat"
    RHYTHM = "rhythm"
    EVENT = "event"
    DIAGNOSTIC = "diagnostic"
    VENDOR = "vendor"


@dataclass(frozen=True)
class Annotation:
    """A single annotation preserved exactly as provided by the source recording."""

    annotation_type: AnnotationType
    label: str
    sample_index: int | None = None
    time_offset_seconds: float | None = None
    lead: CanonicalLead | None = None
    source: str | None = None


@dataclass(frozen=True)
class Annotations:
    """The ordered collection of annotations for one ECGRecord. May be empty."""

    items: tuple[Annotation, ...] = field(default_factory=tuple)

    def is_empty(self) -> bool:
        return not self.items

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)
