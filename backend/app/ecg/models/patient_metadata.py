"""PatientMetadata domain object.

Describes the individual, never the recording (Implementation Spec 4.5 /
5.5). Every field is optional at the source level -- absence in the
uploaded file is not an error. If patient metadata is unavailable, an empty
PatientMetadata object is still created and flagged for manual completion
(Business Rule 8.6).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date

_OPTIONAL_FIELDS = (
    "patient_id",
    "name",
    "date_of_birth",
    "age",
    "sex",
    "hospital",
    "clinician",
    "clinical_history",
)


@dataclass(frozen=True)
class PatientMetadata:
    """Patient-related information. May be entirely empty."""

    patient_id: str | None = None
    name: str | None = None
    date_of_birth: date | None = None
    age: int | None = None
    sex: str | None = None
    hospital: str | None = None
    clinician: str | None = None
    clinical_history: str | None = None

    def missing_fields(self) -> tuple[str, ...]:
        """Fields not present in the source recording, for manual completion."""
        return tuple(name for name in _OPTIONAL_FIELDS if getattr(self, name) is None)

    def is_empty(self) -> bool:
        return len(self.missing_fields()) == len(fields(self))
