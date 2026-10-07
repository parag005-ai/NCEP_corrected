"""Small type-coercion helpers shared by the metadata extractors.

Raw parser output is always strings or simple scalars keyed inconsistently
across formats (e.g. WFDB comment key "age" vs DICOM tag "PatientAge" vs an
XML attribute "age"). Extractors look up several candidate keys and coerce
loosely-typed raw values into the domain model's typed fields. These
helpers never fabricate a value -- they return None when nothing usable is
present (Implementation Spec 12.7 Extraction Policy: "If a field is absent
... do not fabricate values").
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def first(info: dict[str, Any], *keys: str) -> str | None:
    """Case-insensitive lookup of the first present, non-empty key."""
    lowered = {str(k).lower(): v for k, v in info.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return str(value).strip()
    return None


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


_DATE_FORMATS = ("%Y-%m-%d", "%Y%m%d", "%d-%b-%Y", "%d/%m/%Y", "%m/%d/%Y")


def parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


_DATETIME_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S")

# A source may only supply a date with no time component (e.g. a DICOM
# StudyDate with no StudyTime). Rather than silently discarding the date
# because no time-bearing format matches, these are tried as a fallback and
# normalized to midnight -- still "the date is known", never fabricating a
# time that was not actually recorded.
_DATE_ONLY_FALLBACK_FORMATS = ("%Y-%m-%d", "%Y%m%d", "%d-%b-%Y", "%d/%m/%Y", "%m/%d/%Y")


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    for fmt in _DATE_ONLY_FALLBACK_FORMATS:
        try:
            return datetime.combine(datetime.strptime(value, fmt).date(), datetime.min.time())
        except ValueError:
            continue
    return None
