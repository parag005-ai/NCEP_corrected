"""Baseline wander removal for ECG preprocessing.

Uses the standard two-stage median-filter technique: a ~200ms window
removes the QRS complex, leaving P/T waves and drift; a ~600ms window then
removes the P/T waves, leaving an estimate of the slow baseline wander
alone, which is subtracted from the (already bandpass-filtered) signal.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import medfilt

QRS_WINDOW_SECONDS = 0.2
PT_WAVE_WINDOW_SECONDS = 0.6


def _odd(n: int) -> int:
    n = max(1, n)
    return n if n % 2 == 1 else n + 1


def remove_baseline_wander(samples: np.ndarray, sampling_rate_hz: float) -> np.ndarray:
    """Estimates and subtracts baseline wander from `samples`."""
    window_qrs = _odd(round(QRS_WINDOW_SECONDS * sampling_rate_hz))
    window_pt = _odd(round(PT_WAVE_WINDOW_SECONDS * sampling_rate_hz))

    if samples.shape[0] <= window_pt:
        return samples - np.median(samples)

    stage1 = medfilt(samples, kernel_size=window_qrs)
    baseline = medfilt(stage1, kernel_size=window_pt)
    return samples - baseline
