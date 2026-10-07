"""Signal validation, lead selection and window selection (Sprint 4.6 - 4.8).

Three decisions stand between a loaded recording and a drawable strip: is the
signal structurally usable, which lead is displayed, and which segment of it.
All three are deterministic -- the same recording always yields the same
strip (Sprint 4.14) -- and none of them interprets the signal clinically.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from app.ecg.constants import CANONICAL_LEAD_ORDER
from app.reporting.visualizations.rendering_policy import DEFAULT_WINDOW_SECONDS

#: Lead II is the default rhythm lead: it gives the clearest P-QRS-T sequence
#: for standard rhythm interpretation (Sprint 4.7).
DEFAULT_LEAD = "II"

#: Tried in order when lead II is absent, before falling back to the first
#: available canonical lead (Sprint 4.7).
FALLBACK_LEADS: tuple[str, ...] = ("I", "V5", "V1")


@dataclass(frozen=True)
class SignalValidation:
    """Whether a recording can be drawn at all, and why not when it cannot."""

    is_usable: bool
    reason: str | None = None

    @classmethod
    def usable(cls) -> "SignalValidation":
        return cls(is_usable=True)

    @classmethod
    def unusable(cls, reason: str) -> "SignalValidation":
        return cls(is_usable=False, reason=reason)


@dataclass(frozen=True)
class VisualizationWindow:
    """The segment of the recording that is drawn."""

    start_second: float
    end_second: float
    start_index: int
    end_index: int

    @property
    def duration_seconds(self) -> float:
        return self.end_second - self.start_second


def validate_signal(sampling_rate_hz: float, leads: Mapping[str, np.ndarray]) -> SignalValidation:
    """Checks that a recording is structurally drawable (Sprint 4.6).

    Verifies waveform and lead availability, a usable sampling frequency, a
    non-empty duration and numeric integrity. A recording that fails any check
    is not drawn at all: an approximated or partially blank strip would
    misrepresent the recording (Sprint 4.14 No Fabrication Policy).
    """
    if not leads:
        return SignalValidation.unusable("the recording contains no leads")
    if not np.isfinite(sampling_rate_hz) or sampling_rate_hz <= 0:
        return SignalValidation.unusable(
            f"the recording has an unusable sampling rate ({sampling_rate_hz})"
        )
    if all(samples.size == 0 for samples in leads.values()):
        return SignalValidation.unusable("the recording contains no samples")
    if not any(np.isfinite(samples).all() and samples.size > 0 for samples in leads.values()):
        return SignalValidation.unusable("no lead contains a continuous, numerically valid signal")
    return SignalValidation.usable()


def select_lead(leads: Mapping[str, np.ndarray]) -> str | None:
    """Chooses the lead to display, or None when no lead is usable (Sprint 4.7).

    A lead qualifies only if it actually carries a finite signal, so the
    fallback chain skips a present-but-empty or corrupt lead rather than
    drawing it.
    """
    usable = {
        name for name, samples in leads.items() if samples.size > 0 and np.isfinite(samples).all()
    }
    if not usable:
        return None

    for candidate in (DEFAULT_LEAD, *FALLBACK_LEADS):
        if candidate in usable:
            return candidate
    for canonical in CANONICAL_LEAD_ORDER:
        if canonical.value in usable:
            return canonical.value
    return sorted(usable)[0]


def select_window(
    sample_count: int,
    sampling_rate_hz: float,
    *,
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
) -> VisualizationWindow:
    """Chooses the displayed segment of the recording (Sprint 4.8).

    A representative strip rather than the whole recording: readable at a
    standard paper speed, consistent across reports, and quick to render. The
    segment starts at the beginning of the recording -- choosing a "better"
    offset would be a clinical judgement, which this engine does not make. The
    complete recording remains available as the stored waveform artifact.
    """
    available_seconds = sample_count / sampling_rate_hz
    duration = min(window_seconds, available_seconds)
    return VisualizationWindow(
        start_second=0.0,
        end_second=duration,
        start_index=0,
        end_index=int(round(duration * sampling_rate_hz)),
    )
