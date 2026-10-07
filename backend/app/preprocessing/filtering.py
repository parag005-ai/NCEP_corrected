"""Signal filtering for ECG preprocessing.

Removes noise outside the clinically relevant ECG frequency band and
suppresses mains-frequency interference, before any downstream stage
(baseline correction, beat detection, quality scoring) sees the signal.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt, iirnotch

BANDPASS_LOW_HZ = 0.5
BANDPASS_HIGH_HZ = 40.0
NOTCH_FREQS_HZ = (50.0, 60.0)
NOTCH_QUALITY_FACTOR = 30.0


def _safe_filtfilt(b: np.ndarray, a: np.ndarray, samples: np.ndarray) -> np.ndarray:
    """Applies filtfilt, or returns the input unchanged if it's too short to pad.

    filtfilt requires more samples than its default pad length; very short
    recordings (or a handful of stray leads) would otherwise raise instead
    of degrading gracefully.
    """
    padlen = 3 * max(len(a), len(b))
    if samples.shape[0] <= padlen:
        return samples
    return filtfilt(b, a, samples)


def bandpass_filter(samples: np.ndarray, sampling_rate_hz: float) -> np.ndarray:
    """Zero-phase Butterworth bandpass, isolating the 0.5-40 Hz ECG band."""
    nyquist = sampling_rate_hz / 2.0
    low = BANDPASS_LOW_HZ / nyquist
    high = min(BANDPASS_HIGH_HZ, nyquist * 0.99) / nyquist
    b, a = butter(N=4, Wn=[low, high], btype="bandpass")
    return _safe_filtfilt(b, a, samples)


def notch_filter(samples: np.ndarray, sampling_rate_hz: float) -> np.ndarray:
    """Zero-phase notch filter suppressing 50 Hz and 60 Hz mains interference."""
    nyquist = sampling_rate_hz / 2.0
    filtered = samples
    for freq in NOTCH_FREQS_HZ:
        if freq >= nyquist:
            continue
        b, a = iirnotch(w0=freq / nyquist, Q=NOTCH_QUALITY_FACTOR)
        filtered = _safe_filtfilt(b, a, filtered)
    return filtered


def apply_filters(samples: np.ndarray, sampling_rate_hz: float) -> np.ndarray:
    """Applies the bandpass filter followed by mains notch filtering."""
    return notch_filter(bandpass_filter(samples, sampling_rate_hz), sampling_rate_hz)
