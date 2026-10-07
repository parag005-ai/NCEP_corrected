"""Computed signal-quality scoring for ECG preprocessing.

Unlike `app.ingestion`'s QualityMetadataExtractor (which only ever passes
through quality indicators already present in the source file),
this stage computes new quality metrics from the processed waveform
itself -- exactly the responsibility Phase 1 ingestion explicitly defers
to preprocessing (see `app.ecg.models.quality_metadata`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

FLATLINE_STD_THRESHOLD = 1e-6
CLIPPING_FRACTION_THRESHOLD = 0.01
MIN_ACCEPTABLE_SNR_DB = 4.0
SNR_SCORE_CEILING_DB = 20.0
MIN_EXPECTED_HEART_RATE_BPM = 30.0


@dataclass(frozen=True)
class SignalQualityResult:
    """0.0 (unusable) - 1.0 (clean), plus the specific issues that were found."""

    quality_score: float
    flags: tuple[str, ...] = field(default_factory=tuple)


def _estimate_snr_db(raw: np.ndarray, filtered: np.ndarray) -> float:
    """Rough SNR estimate: filtered signal power vs. the power removed as noise."""
    noise = raw - filtered
    signal_power = np.mean(filtered**2)
    noise_power = np.mean(noise**2)
    if noise_power < 1e-12:
        return 100.0
    if signal_power < 1e-12:
        return -100.0
    return float(10 * np.log10(signal_power / noise_power))


def _is_clipped(raw: np.ndarray) -> bool:
    """Flags a lead where >1% of samples sit at the observed min/max (saturation)."""
    if raw.size == 0:
        return False
    lo, hi = raw.min(), raw.max()
    if lo == hi:
        return False
    at_bounds = np.count_nonzero((raw <= lo) | (raw >= hi))
    return (at_bounds / raw.size) > CLIPPING_FRACTION_THRESHOLD


def assess_quality(
    raw: np.ndarray, filtered: np.ndarray, beat_count: int, duration_seconds: float
) -> SignalQualityResult:
    flags: list[str] = []

    if np.std(raw) < FLATLINE_STD_THRESHOLD:
        flags.append("flatline")
    if _is_clipped(raw):
        flags.append("clipping")

    snr_db = _estimate_snr_db(raw, filtered)
    if snr_db < MIN_ACCEPTABLE_SNR_DB:
        flags.append("low_snr")

    expected_min_beats = duration_seconds * (MIN_EXPECTED_HEART_RATE_BPM / 60.0)
    if duration_seconds >= 2.0 and beat_count < expected_min_beats:
        flags.append("sparse_beats")

    score = float(np.clip(snr_db / SNR_SCORE_CEILING_DB, 0.0, 1.0))
    if "flatline" in flags:
        score = 0.0

    return SignalQualityResult(quality_score=score, flags=tuple(flags))
