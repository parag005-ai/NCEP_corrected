"""QualityMetadata domain object.

Preserves quality indicators that already exist in the source recording.
Phase 1 never computes new quality metrics (Implementation Spec 3.7 /
12.11) -- that belongs to preprocessing/analysis in later phases.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QualityMetadata:
    """Quality indicators sourced directly from the recording, never computed."""

    quality_flags: tuple[str, ...] = field(default_factory=tuple)
    noise_indicators: tuple[str, ...] = field(default_factory=tuple)
    device_warnings: tuple[str, ...] = field(default_factory=tuple)
    recording_confidence: float | None = None

    def is_empty(self) -> bool:
        return (
            not self.quality_flags
            and not self.noise_indicators
            and not self.device_warnings
            and self.recording_confidence is None
        )
