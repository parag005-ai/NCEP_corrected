"""R-peak (beat) detection for ECG preprocessing."""

from __future__ import annotations

from dataclasses import dataclass

import neurokit2 as nk
import numpy as np

MIN_SAMPLES_FOR_DETECTION_SECONDS = 1.0


@dataclass(frozen=True)
class BeatDetectionResult:
    r_peak_indices: tuple[int, ...]
    beat_count: int
    mean_heart_rate_bpm: float | None


def detect_beats(samples: np.ndarray, sampling_rate_hz: float) -> BeatDetectionResult:
    """Detects R-peaks and derives the mean heart rate for one lead.

    Falls back to an empty result rather than raising when a stable QRS
    pattern can't be found (very short or heavily corrupted leads) --
    preprocessing must never abort the whole pipeline over one bad lead.
    """
    if samples.shape[0] < int(MIN_SAMPLES_FOR_DETECTION_SECONDS * sampling_rate_hz):
        return BeatDetectionResult((), 0, None)

    try:
        _, info = nk.ecg_peaks(samples, sampling_rate=sampling_rate_hz)
        peaks = tuple(int(p) for p in info.get("ECG_R_Peaks", []))
    except Exception:
        return BeatDetectionResult((), 0, None)

    if len(peaks) < 2:
        return BeatDetectionResult(peaks, len(peaks), None)

    rr_intervals_s = np.diff(peaks) / sampling_rate_hz
    mean_hr = float(60.0 / np.mean(rr_intervals_s)) if rr_intervals_s.size else None
    return BeatDetectionResult(peaks, len(peaks), mean_hr)
