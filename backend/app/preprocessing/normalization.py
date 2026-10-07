"""Per-lead amplitude normalization for ECG preprocessing."""

from __future__ import annotations

import numpy as np

FLAT_SIGNAL_STD_THRESHOLD = 1e-9


def z_score_normalize(samples: np.ndarray) -> np.ndarray:
    """Normalizes a lead to zero mean and unit variance.

    Falls back to mean-centering only when the signal has ~zero variance
    (e.g. a flatlined lead), so a degenerate lead never divides by ~0.
    """
    std = np.std(samples)
    if std < FLAT_SIGNAL_STD_THRESHOLD:
        return samples - np.mean(samples)
    return (samples - np.mean(samples)) / std
