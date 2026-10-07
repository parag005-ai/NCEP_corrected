"""Maps source-specific ECG lead identifiers to the canonical NCEP lead model.

Implementation Spec 9.5 -- "Each parser is responsible for mapping source
lead identifiers into the canonical NCEP lead names... If a lead cannot be
mapped unambiguously, the parser shall report a validation error rather than
guessing."

This module owns the alias table so every parser resolves lead names the
same way instead of re-implementing ad-hoc mapping logic.
"""

from __future__ import annotations

from app.ecg.constants import CanonicalLead
from app.ingestion.exceptions import UnmappableLeadError

# Aliases are matched case-insensitively and with surrounding whitespace and
# separator characters (spaces, underscores, hyphens) stripped. Each source
# format may register additional aliases via `register_alias` at import
# time (e.g. a DICOM code meaning "Lead I") without editing this table.
_BASE_ALIASES: dict[str, CanonicalLead] = {
    "i": CanonicalLead.I,
    "leadi": CanonicalLead.I,
    "ii": CanonicalLead.II,
    "leadii": CanonicalLead.II,
    "iii": CanonicalLead.III,
    "leadiii": CanonicalLead.III,
    "avr": CanonicalLead.aVR,
    "avl": CanonicalLead.aVL,
    "avf": CanonicalLead.aVF,
    "v1": CanonicalLead.V1,
    "v2": CanonicalLead.V2,
    "v3": CanonicalLead.V3,
    "v4": CanonicalLead.V4,
    "v5": CanonicalLead.V5,
    "v6": CanonicalLead.V6,
    "x": CanonicalLead.X,
    "vx": CanonicalLead.X,
    "frankx": CanonicalLead.X,
    "y": CanonicalLead.Y,
    "vy": CanonicalLead.Y,
    "franky": CanonicalLead.Y,
    "z": CanonicalLead.Z,
    "vz": CanonicalLead.Z,
    "frankz": CanonicalLead.Z,
}

_ALIASES: dict[str, CanonicalLead] = dict(_BASE_ALIASES)


def _normalize(raw_name: str) -> str:
    return "".join(ch for ch in raw_name.strip().lower() if ch.isalnum())


def register_alias(raw_name: str, canonical: CanonicalLead) -> None:
    """Register an additional source-specific alias for a canonical lead.

    Intended to be called by format-specific parsers for vendor codes that
    are unambiguous but not part of the shared base table (e.g. a numeric
    DICOM waveform channel source code).
    """
    _ALIASES[_normalize(raw_name)] = canonical


def try_resolve_canonical_lead(raw_name: str) -> CanonicalLead | None:
    """Resolve a source lead identifier to a canonical lead, or None if unknown."""
    normalized = _normalize(raw_name)
    resolved = _ALIASES.get(normalized)
    if resolved is not None:
        return resolved
    # Fall back to stripping a "lead" prefix, e.g. DICOM ChannelSourceSequence
    # code meanings such as "Lead aVR" or "Lead V1" that are not literally
    # enumerated in the base alias table.
    if normalized.startswith("lead") and len(normalized) > 4:
        return _ALIASES.get(normalized[4:])
    return None


def resolve_canonical_lead(raw_name: str) -> CanonicalLead:
    """Resolve a source lead identifier to a canonical lead.

    Raises:
        UnmappableLeadError: if the identifier cannot be mapped unambiguously.
            Per Implementation Spec 9.5, callers must never guess or
            fabricate a mapping.
    """
    resolved = try_resolve_canonical_lead(raw_name)
    if resolved is None:
        raise UnmappableLeadError(f"Lead identifier {raw_name!r} could not be mapped to a canonical NCEP lead.")
    return resolved
