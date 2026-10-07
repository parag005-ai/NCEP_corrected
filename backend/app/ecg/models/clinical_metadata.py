"""ClinicalMetadata domain object.

Preserves clinical information accompanying a recording exactly as
provided, with no interpretation (Implementation Spec 3.7 / 12.9). Phase 1
never generates or infers clinical content.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClinicalMetadata:
    """Clinical context accompanying the recording, preserved verbatim."""

    diagnosis: str | None = None
    reason_for_examination: str | None = None
    medications: tuple[str, ...] = field(default_factory=tuple)
    procedure_notes: str | None = None
    clinical_comments: str | None = None

    def is_empty(self) -> bool:
        return (
            self.diagnosis is None
            and self.reason_for_examination is None
            and not self.medications
            and self.procedure_notes is None
            and self.clinical_comments is None
        )
