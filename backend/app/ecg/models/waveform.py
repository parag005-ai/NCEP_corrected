"""Waveform domain objects.

Waveform represents only electrical signal data (Implementation Spec 4.4 /
5.4). It never contains patient identifiers, hospital information,
diagnosis, or device information. Once constructed, a Waveform is
immutable -- no ingestion stage after the parser may modify sample values
(Business Rule 8.19, Builder Rule 13.9.2).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.ecg.constants import CANONICAL_LEAD_ORDER, FRANK_ORTHOGONAL_LEADS, CanonicalLead, DEFAULT_SIGNAL_UNITS


@dataclass(frozen=True)
class LeadSignal:
    """The ordered sample sequence acquired for a single canonical lead."""

    lead: CanonicalLead
    samples: np.ndarray

    def __post_init__(self) -> None:
        if self.samples.ndim != 1:
            raise ValueError(f"LeadSignal samples for {self.lead.value} must be 1-dimensional.")
        samples = np.asarray(self.samples, dtype=np.float64)
        samples.setflags(write=False)
        object.__setattr__(self, "samples", samples)

    @property
    def sample_count(self) -> int:
        return int(self.samples.shape[0])


@dataclass(frozen=True)
class Waveform:
    """The standardized NCEP waveform representation for one recording.

    All leads present share a single time base: the same sampling rate and
    the same acquisition interval (Implementation Spec 9.7). Leads absent
    from the source recording are simply absent from `leads` -- they are
    never synthesized (9.4, 9.13).
    """

    leads: dict[CanonicalLead, LeadSignal] = field(default_factory=dict)
    sampling_rate_hz: float = 0.0
    units: str = DEFAULT_SIGNAL_UNITS

    def __post_init__(self) -> None:
        if not self.leads:
            raise ValueError("Waveform must contain at least one lead.")
        if self.sampling_rate_hz <= 0:
            raise ValueError("Waveform sampling_rate_hz must be positive.")

        counts = {signal.sample_count for signal in self.leads.values()}
        if len(counts) > 1:
            raise ValueError(f"All leads must share the same sample count; found {sorted(counts)}.")

        for lead, signal in self.leads.items():
            if signal.lead is not lead:
                raise ValueError(f"Lead key {lead.value} does not match LeadSignal.lead {signal.lead.value}.")

        object.__setattr__(self, "leads", dict(self.leads))

    @property
    def sample_count(self) -> int:
        return next(iter(self.leads.values())).sample_count

    @property
    def duration_seconds(self) -> float:
        return self.sample_count / self.sampling_rate_hz

    @property
    def available_leads(self) -> tuple[CanonicalLead, ...]:
        return tuple(lead for lead in CANONICAL_LEAD_ORDER if lead in self.leads)

    @property
    def lead_count(self) -> int:
        return len(self.leads)

    @property
    def xyz_available(self) -> bool:
        return any(lead in self.leads for lead in FRANK_ORTHOGONAL_LEADS)

    def get(self, lead: CanonicalLead) -> LeadSignal | None:
        return self.leads.get(lead)
