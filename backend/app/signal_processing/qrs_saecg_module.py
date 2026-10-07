import numpy as np


# ============================================================
# QRS SAECG configuration
# ============================================================

PRE_QRS_MS = 100
POST_QRS_MS = 120

MIN_QRS_MS = 50
MAX_QRS_MS = 220

# Controlled fallback
FALLBACK_MIN_QRS_MS = 40
FALLBACK_THRESHOLD_FRACTION = 0.01

# Additional adaptive boundary fallback.
# This allows short below-threshold gaps inside the QRS
# instead of incorrectly breaking the QRS into fragments.
ADAPTIVE_THRESHOLD_FRACTIONS = (
    0.005,
    0.0025,
    0.001
)

MAX_ALLOWED_GAP_MS = 10.0
ADAPTIVE_MIN_QRS_MS = 40

MIN_CORRELATION = 0.90

EPS = 1e-12


# ============================================================
# Utility helpers
# ============================================================

def _is_valid_number(value):
    try:
        return np.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _safe_array(signal):
    try:
        arr = np.asarray(signal, dtype=float).flatten()
    except Exception:
        return None

    if arr.size == 0:
        return None

    if not np.all(np.isfinite(arr)):
        return None

    return arr


# ============================================================
# Beat extraction
# ============================================================

def extract_beats(signal, r_peaks, fs,
                  pre_ms=PRE_QRS_MS,
                  post_ms=POST_QRS_MS):

    signal = _safe_array(signal)

    if signal is None:
        return []

    if not _is_valid_number(fs) or fs <= 0:
        return []

    if r_peaks is None:
        return []

    pre_samples = int(round(pre_ms * fs / 1000.0))
    post_samples = int(round(post_ms * fs / 1000.0))

    beats = []

    for r in r_peaks:

        try:
            r = int(round(float(r)))
        except (TypeError, ValueError):
            continue

        start = r - pre_samples
        end = r + post_samples + 1

        if start < 0:
            continue

        if end > len(signal):
            continue

        beat = signal[start:end]

        expected_length = (
            pre_samples
            + post_samples
            + 1
        )

        if len(beat) != expected_length:
            continue

        if not np.all(np.isfinite(beat)):
            continue

        beats.append(
            np.asarray(beat, dtype=float)
        )

    return beats


# ============================================================
# Beat alignment
# ============================================================

def align_beats(beats, r_index):

    if beats is None or len(beats) == 0:
        return []

    aligned = []

    target = int(r_index)

    for beat in beats:

        beat = _safe_array(beat)

        if beat is None:
            continue

        if target < 0 or target >= len(beat):
            continue

        aligned.append(
            np.asarray(beat, dtype=float).copy()
        )

    return aligned


# ============================================================
# Bad-beat rejection
# ============================================================

def reject_bad_beats(
        beats,
        threshold=MIN_CORRELATION):

    if beats is None or len(beats) == 0:
        return [], 0

    valid_beats = []

    for beat in beats:

        arr = _safe_array(beat)

        if arr is not None:
            valid_beats.append(arr)

    if len(valid_beats) == 0:
        return [], 0

    if len(valid_beats) == 1:
        return [valid_beats[0]], 0

    try:
        reference = np.median(
            np.vstack(valid_beats),
            axis=0
        )
    except Exception:
        return valid_beats, 0

    reference_centered = (
        reference - np.mean(reference)
    )

    reference_norm = np.linalg.norm(
        reference_centered
    )

    if reference_norm <= EPS:
        return valid_beats, 0

    accepted = []
    rejected = 0

    for beat in valid_beats:

        centered = (
            beat - np.mean(beat)
        )

        beat_norm = np.linalg.norm(
            centered
        )

        if beat_norm <= EPS:
            rejected += 1
            continue

        correlation = (
            np.dot(
                centered,
                reference_centered
            )
            / (
                beat_norm
                * reference_norm
            )
        )

        if not np.isfinite(correlation):
            rejected += 1
            continue

        if correlation >= threshold:
            accepted.append(beat)
        else:
            rejected += 1

    return accepted, rejected


# ============================================================
# SAECG construction
# ============================================================

def build_qrs_saecg(signal, r_peaks, fs):

    signal = _safe_array(signal)

    if signal is None:
        return None, 0, 0, 0

    if not _is_valid_number(fs) or fs <= 0:
        return None, 0, 0, 0

    if r_peaks is None or len(r_peaks) == 0:
        return None, 0, 0, 0

    pre_samples = int(
        round(
            PRE_QRS_MS
            * fs
            / 1000.0
        )
    )

    extracted = extract_beats(
        signal,
        r_peaks,
        fs,
        pre_ms=PRE_QRS_MS,
        post_ms=POST_QRS_MS
    )

    beats_extracted = len(extracted)

    if beats_extracted == 0:
        return None, 0, 0, 0

    aligned = align_beats(
        extracted,
        pre_samples
    )

    if len(aligned) == 0:
        return None, beats_extracted, 0, 0

    accepted, rejected = reject_bad_beats(
        aligned,
        threshold=MIN_CORRELATION
    )

    beats_used = len(accepted)

    if beats_used == 0:
        return None, beats_extracted, 0, rejected

    try:
        average_waveform = np.median(
            np.vstack(accepted),
            axis=0
        )
    except Exception:
        return None, beats_extracted, beats_used, rejected

    average_waveform = _safe_array(
        average_waveform
    )

    if average_waveform is None:
        return None, beats_extracted, beats_used, rejected

    return (
        average_waveform,
        beats_extracted,
        beats_used,
        rejected
    )


# ============================================================
# Basic contiguous QRS boundary detection
# ============================================================

def _find_contiguous_qrs_region(
        waveform,
        local_r,
        threshold):

    amplitude = np.abs(waveform)

    if local_r < 0 or local_r >= len(waveform):
        return None, None

    if amplitude[local_r] < threshold:
        return None, None

    onset = local_r
    offset = local_r

    while onset > 0:

        if amplitude[onset - 1] < threshold:
            break

        onset -= 1

    while offset < len(waveform) - 1:

        if amplitude[offset + 1] < threshold:
            break

        offset += 1

    if onset >= local_r:
        return None, None

    if offset <= local_r:
        return None, None

    return onset, offset


# ============================================================
# Adaptive QRS boundary detection
# ============================================================

def _find_qrs_region_with_gap_tolerance(
        waveform,
        local_r,
        threshold,
        max_gap_samples):

    """
    Find a QRS region around R while allowing short
    below-threshold gaps.

    This is useful when a signal-averaged QRS has small
    amplitude dips between Q, R and S components.

    The search stops only after the below-threshold gap
    exceeds the allowed duration.
    """

    amplitude = np.abs(waveform)

    if (
        local_r < 0
        or local_r >= len(waveform)
    ):
        return None, None

    if amplitude[local_r] < threshold:
        return None, None

    # --------------------------------------------------------
    # Search left
    # --------------------------------------------------------

    onset = local_r
    gap = 0

    while onset > 0:

        previous = onset - 1

        if amplitude[previous] >= threshold:
            gap = 0
            onset = previous
            continue

        gap += 1

        if gap > max_gap_samples:
            break

        onset = previous

    # Remove the trailing below-threshold gap.
    onset += gap

    # --------------------------------------------------------
    # Search right
    # --------------------------------------------------------

    offset = local_r
    gap = 0

    while offset < len(waveform) - 1:

        following = offset + 1

        if amplitude[following] >= threshold:
            gap = 0
            offset = following
            continue

        gap += 1

        if gap > max_gap_samples:
            break

        offset = following

    # Remove the trailing below-threshold gap.
    offset -= gap

    if onset >= local_r:
        return None, None

    if offset <= local_r:
        return None, None

    return onset, offset


# ============================================================
# QRS metric calculation
# ============================================================

def _calculate_qrs_metrics(
        waveform,
        local_r,
        fs,
        threshold_fraction,
        minimum_duration_ms):

    amplitude = np.abs(waveform)

    if (
        local_r < 0
        or local_r >= len(waveform)
    ):
        return None

    peak = float(
        amplitude[local_r]
    )

    if (
        not np.isfinite(peak)
        or peak <= EPS
    ):
        return None

    threshold = (
        threshold_fraction
        * peak
    )

    onset, offset = (
        _find_contiguous_qrs_region(
            waveform,
            local_r,
            threshold
        )
    )

    if onset is None or offset is None:
        return None

    duration_ms = (
        (offset - onset)
        * 1000.0
        / fs
    )

    if duration_ms < minimum_duration_ms:
        return None

    if duration_ms > MAX_QRS_MS:
        return None

    return _finish_qrs_metrics(
        waveform,
        onset,
        offset,
        peak,
        fs,
        duration_ms
    )


# ============================================================
# Adaptive QRS metric calculation
# ============================================================

def _calculate_adaptive_qrs_metrics(
        waveform,
        local_r,
        fs):

    amplitude = np.abs(waveform)

    if (
        local_r < 0
        or local_r >= len(waveform)
    ):
        return None

    peak = float(
        amplitude[local_r]
    )

    if (
        not np.isfinite(peak)
        or peak <= EPS
    ):
        return None

    max_gap_samples = max(
        1,
        int(
            round(
                MAX_ALLOWED_GAP_MS
                * fs
                / 1000.0
            )
        )
    )

    for threshold_fraction in (
        ADAPTIVE_THRESHOLD_FRACTIONS
    ):

        threshold = (
            threshold_fraction
            * peak
        )

        onset, offset = (
            _find_qrs_region_with_gap_tolerance(
                waveform,
                local_r,
                threshold,
                max_gap_samples
            )
        )

        if onset is None or offset is None:
            continue

        duration_ms = (
            (offset - onset)
            * 1000.0
            / fs
        )

        if duration_ms < ADAPTIVE_MIN_QRS_MS:
            continue

        if duration_ms > MAX_QRS_MS:
            continue

        metrics = _finish_qrs_metrics(
            waveform,
            onset,
            offset,
            peak,
            fs,
            duration_ms
        )

        if metrics is not None:
            return metrics

    return None


# ============================================================
# Finish QRS metrics
# ============================================================

def _finish_qrs_metrics(
        waveform,
        onset,
        offset,
        peak,
        fs,
        duration_ms):

    # --------------------------------------------------------
    # RMS40
    # --------------------------------------------------------

    forty_ms_samples = int(
        round(
            40.0
            * fs
            / 1000.0
        )
    )

    if forty_ms_samples <= 0:
        return None

    rms_start = max(
        onset,
        offset
        - forty_ms_samples
        + 1
    )

    terminal_segment = waveform[
        rms_start:offset + 1
    ]

    if len(terminal_segment) == 0:
        return None

    rms40 = float(
        np.sqrt(
            np.mean(
                np.square(
                    terminal_segment
                )
            )
        )
    )

    if not np.isfinite(rms40):
        return None

    # --------------------------------------------------------
    # LAS40
    #
    # Existing project methodology retained:
    # terminal QRS region below 20% of peak amplitude.
    #
    # This is NOT the conventional fixed 40-uV definition.
    # It is retained here because changing calibration or
    # methodology without confirmation would alter the
    # project's measurement definition.
    # --------------------------------------------------------

    las_threshold = (
        0.20 * peak
    )

    below_indices = np.where(
        np.abs(
            waveform[
                onset:offset + 1
            ]
        )
        < las_threshold
    )[0]

    if len(below_indices) == 0:

        las40_ms = 0.0

    else:

        last_below = (
            onset
            + int(
                below_indices[-1]
            )
        )

        las40_ms = (
            (offset - last_below)
            * 1000.0
            / fs
        )

        if las40_ms < 0:
            las40_ms = 0.0

    if not np.isfinite(las40_ms):
        return None

    return (
        float(duration_ms),
        float(rms40),
        float(las40_ms)
    )


# ============================================================
# QRS LP metrics
# ============================================================

def compute_qrs_lp_metrics(
        average_waveform,
        r_index,
        fs):

    """
    Calculate:

        Filtered_QRS_Duration_ms
        QRS_RMS40_mV
        QRS_LAS40_ms

    Boundary strategy:

        1. 2% threshold, minimum 50 ms
        2. 1% threshold, minimum 40 ms
        3. Adaptive threshold with short-gap tolerance

    All accepted durations must remain within
    40-220 ms.

    Invalid measurements remain NaN.
    """

    waveform = _safe_array(
        average_waveform
    )

    if waveform is None:
        return np.nan, np.nan, np.nan

    if (
        not _is_valid_number(fs)
        or fs <= 0
    ):
        return np.nan, np.nan, np.nan

    try:
        r_index = int(
            round(float(r_index))
        )
    except (
        TypeError,
        ValueError
    ):
        return np.nan, np.nan, np.nan

    if (
        r_index < 0
        or r_index >= len(waveform)
    ):
        return np.nan, np.nan, np.nan

    # --------------------------------------------------------
    # Find strongest local QRS point.
    # --------------------------------------------------------

    search_radius = int(
        round(
            40.0
            * fs
            / 1000.0
        )
    )

    search_start = max(
        0,
        r_index - search_radius
    )

    search_end = min(
        len(waveform),
        r_index
        + search_radius
        + 1
    )

    local_region = np.abs(
        waveform[
            search_start:search_end
        ]
    )

    if len(local_region) == 0:
        return np.nan, np.nan, np.nan

    local_peak_offset = int(
        np.argmax(local_region)
    )

    local_r = (
        search_start
        + local_peak_offset
    )

    peak = float(
        np.abs(waveform[local_r])
    )

    if (
        not np.isfinite(peak)
        or peak <= EPS
    ):
        return np.nan, np.nan, np.nan

    # --------------------------------------------------------
    # Expected QRS analysis window:
    #
    # 100 ms before R
    # 120 ms after R
    # --------------------------------------------------------

    window_start = max(
        0,
        r_index
        - int(
            round(
                100.0
                * fs
                / 1000.0
            )
        )
    )

    window_end = min(
        len(waveform),
        r_index
        + int(
            round(
                120.0
                * fs
                / 1000.0
            )
        )
        + 1
    )

    if window_end <= window_start:
        return np.nan, np.nan, np.nan

    waveform_window = waveform[
        window_start:window_end
    ]

    window_local_r = (
        local_r - window_start
    )

    if (
        window_local_r < 0
        or window_local_r
        >= len(waveform_window)
    ):
        return np.nan, np.nan, np.nan

    # --------------------------------------------------------
    # 1. Primary: 2%
    # --------------------------------------------------------

    primary = _calculate_qrs_metrics(
        waveform_window,
        window_local_r,
        fs,
        threshold_fraction=0.02,
        minimum_duration_ms=MIN_QRS_MS
    )

    if primary is not None:
        return primary

    # --------------------------------------------------------
    # 2. Controlled fallback: 1%
    # --------------------------------------------------------

    fallback = _calculate_qrs_metrics(
        waveform_window,
        window_local_r,
        fs,
        threshold_fraction=(
            FALLBACK_THRESHOLD_FRACTION
        ),
        minimum_duration_ms=(
            FALLBACK_MIN_QRS_MS
        )
    )

    if fallback is not None:
        return fallback

    # --------------------------------------------------------
    # 3. Adaptive boundary fallback
    #
    # The important difference is that a short dip below
    # threshold does not automatically terminate the QRS.
    # --------------------------------------------------------

    adaptive = _calculate_adaptive_qrs_metrics(
        waveform_window,
        window_local_r,
        fs
    )

    if adaptive is not None:
        return adaptive

    # --------------------------------------------------------
    # No defensible measurement.
    # --------------------------------------------------------

    return np.nan, np.nan, np.nan


# ============================================================
# Main SAECG analysis
# ============================================================

def analyze_qrs_saecg(
        signal,
        r_peaks,
        fs):

    result = {
        "QRS_SAECG_Beats_Extracted": 0,
        "QRS_SAECG_Beats_Used": 0,
        "QRS_SAECG_Beats_Rejected": 0,
        "QRS_SAECG_SNR_dB": np.nan,
        "Filtered_QRS_Duration_ms": np.nan,
        "QRS_RMS40_mV": np.nan,
        "QRS_LAS40_ms": np.nan
    }

    signal = _safe_array(signal)

    if signal is None:
        return result

    if (
        not _is_valid_number(fs)
        or fs <= 0
    ):
        return result

    # Critical safeguard:
    # no R peaks means no QRS-SAECG measurement.
    if (
        r_peaks is None
        or len(r_peaks) == 0
    ):
        return result

    # --------------------------------------------------------
    # Build signal-averaged QRS
    # --------------------------------------------------------

    (
        average_waveform,
        beats_extracted,
        beats_used,
        beats_rejected
    ) = build_qrs_saecg(
        signal,
        r_peaks,
        fs
    )

    result[
        "QRS_SAECG_Beats_Extracted"
    ] = beats_extracted

    result[
        "QRS_SAECG_Beats_Used"
    ] = beats_used

    result[
        "QRS_SAECG_Beats_Rejected"
    ] = beats_rejected

    if average_waveform is None:
        return result

    if beats_used == 0:
        return result

    # --------------------------------------------------------
    # Re-extract accepted beats for SNR
    # --------------------------------------------------------

    pre_samples = int(
        round(
            PRE_QRS_MS
            * fs
            / 1000.0
        )
    )

    extracted = extract_beats(
        signal,
        r_peaks,
        fs,
        pre_ms=PRE_QRS_MS,
        post_ms=POST_QRS_MS
    )

    aligned = align_beats(
        extracted,
        pre_samples
    )

    accepted, _ = reject_bad_beats(
        aligned,
        threshold=MIN_CORRELATION
    )

    # --------------------------------------------------------
    # SNR
    # --------------------------------------------------------

    if len(accepted) > 0:

        try:

            beat_matrix = np.vstack(
                accepted
            )

            signal_component = np.mean(
                beat_matrix,
                axis=0
            )

            noise_component = (
                beat_matrix
                - signal_component
            )

            signal_power = np.mean(
                np.square(
                    signal_component
                )
            )

            noise_power = np.mean(
                np.square(
                    noise_component
                )
            )

            if (
                np.isfinite(signal_power)
                and np.isfinite(noise_power)
                and signal_power > EPS
                and noise_power > EPS
            ):

                snr_db = (
                    10.0
                    * np.log10(
                        signal_power
                        / noise_power
                    )
                )

                if np.isfinite(snr_db):
                    result[
                        "QRS_SAECG_SNR_dB"
                    ] = float(snr_db)

        except Exception:
            pass

    # --------------------------------------------------------
    # LP metrics
    # --------------------------------------------------------

    r_index = int(
        round(
            PRE_QRS_MS
            * fs
            / 1000.0
        )
    )

    (
        filtered_qrs_duration,
        rms40,
        las40
    ) = compute_qrs_lp_metrics(
        average_waveform,
        r_index,
        fs
    )

    result[
        "Filtered_QRS_Duration_ms"
    ] = filtered_qrs_duration

    result[
        "QRS_RMS40_mV"
    ] = rms40

    result[
        "QRS_LAS40_ms"
    ] = las40

    return result