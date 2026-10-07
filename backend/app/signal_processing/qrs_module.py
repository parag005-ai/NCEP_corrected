"""
qrs_module.py
=============

Robust QRS measurement module.

Outputs:
    - QRS duration
    - QRS duration median/mean/std
    - R-peak amplitude
    - Heart rate
    - R-peak count
    - valid QRS beat count
    - QRS QC information
    - actual QRS delineation method used

IMPORTANT:
    This module does NOT force abnormal measurements into a
    "normal" range.

    Implausible or failed measurements remain unavailable
    rather than being artificially corrected.

Input:
    cleaned_signal : 1-D ECG signal
    fs              : sampling frequency in Hz

Return:
    result, r_peaks
"""


import numpy as np
import neurokit2 as nk


# ============================================================
# ENGINEERING / QUALITY-CONTROL LIMITS
# ============================================================

# These are NOT diagnostic thresholds.
#
# They are broad technical limits used to reject obviously
# failed QRS delineation.

MIN_QRS_MS = 50.0
MAX_QRS_MS = 200.0

# RR limits used for heart-rate estimation.
MIN_RR_SEC = 0.30       # 200 bpm
MAX_RR_SEC = 2.00       # 30 bpm

# Robust outlier rejection.
MAX_QRS_DEVIATION_MS = 60.0

# Minimum number of valid beats considered sufficient
# for a stronger patient-level QRS estimate.
MIN_VALID_QRS_BEATS = 3


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _is_valid_number(x):
    """Return True if x is finite and numeric."""
    try:
        return np.isfinite(x)
    except Exception:
        return False


def _clean_index(x):
    """
    Convert NeuroKit index output into an integer sample index.

    Returns None for invalid values.
    """

    if x is None:
        return None

    try:

        if not np.isfinite(x):
            return None

        return int(round(float(x)))

    except Exception:
        return None


def _robust_median(values):
    """Median of finite values."""

    values = np.asarray(
        values,
        dtype=float
    )

    values = values[
        np.isfinite(values)
    ]

    if len(values) == 0:
        return np.nan

    return float(
        np.median(values)
    )


def _robust_mean(values):
    """Mean of finite values."""

    values = np.asarray(
        values,
        dtype=float
    )

    values = values[
        np.isfinite(values)
    ]

    if len(values) == 0:
        return np.nan

    return float(
        np.mean(values)
    )


def _robust_std(values):
    """Standard deviation of finite values."""

    values = np.asarray(
        values,
        dtype=float
    )

    values = values[
        np.isfinite(values)
    ]

    if len(values) == 0:
        return np.nan

    return float(
        np.std(values)
    )


# ============================================================
# R-PEAK DETECTION
# ============================================================

def detect_r_peaks(
    cleaned_signal,
    fs
):
    """
    Detect R peaks using NeuroKit.

    Returns
    -------
    np.ndarray
        Valid R-peak sample indices.
    """

    try:

        _, info = nk.ecg_peaks(
            cleaned_signal,
            sampling_rate=fs,
            method="neurokit"
        )

        r_peaks = np.asarray(
            info.get(
                "ECG_R_Peaks",
                []
            ),
            dtype=int
        )

        # Remove invalid indices.
        r_peaks = r_peaks[
            (r_peaks >= 0)
            &
            (r_peaks < len(cleaned_signal))
        ]

        # Remove duplicates.
        r_peaks = np.unique(
            r_peaks
        )

        return r_peaks

    except Exception as e:

        print(
            f"  [qrs_module] "
            f"R-peak detection failed: {e}"
        )

        return np.array(
            [],
            dtype=int
        )


# ============================================================
# QRS DELINEATION
# ============================================================

def delineate_qrs(
    cleaned_signal,
    r_peaks,
    fs
):
    """
    Try both NeuroKit QRS delineation methods.

    Each method is evaluated by the number of technically
    valid QRS beats.

    A valid QRS beat must satisfy:

        QRS onset < R peak < QRS offset

    and the resulting QRS duration must be within the
    engineering limits.

    The method producing the largest number of valid QRS
    beats is selected.

    Returns
    -------
    waves : dict or None
    method : str or None
    """

    if len(r_peaks) < 2:
        return None, None

    candidates = []

    for method in [
        "dwt",
        "prominence"
    ]:

        try:

            _, waves = nk.ecg_delineate(
                cleaned_signal,
                r_peaks,
                sampling_rate=fs,
                method=method,
                check=True
            )

            if waves is None:
                continue

            q_onsets = waves.get(
                "ECG_R_Onsets",
                []
            )

            q_offsets = waves.get(
                "ECG_R_Offsets",
                []
            )

            valid_count = 0

            for i, r_peak in enumerate(
                r_peaks
            ):

                onset = (
                    q_onsets[i]
                    if i < len(q_onsets)
                    else None
                )

                offset = (
                    q_offsets[i]
                    if i < len(q_offsets)
                    else None
                )

                validated = validate_qrs(
                    onset,
                    r_peak,
                    offset,
                    len(cleaned_signal),
                    fs
                )

                if validated is not None:
                    valid_count += 1

            print(
                f"  [qrs_module] "
                f"{method}: "
                f"{valid_count} valid QRS beats"
            )

            candidates.append(
                (
                    valid_count,
                    method,
                    waves
                )
            )

        except Exception as e:

            print(
                f"  [qrs_module] "
                f"{method} delineation failed: {e}"
            )

    if not candidates:
        return None, None

    # Highest number of technically valid QRS beats wins.
    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    best_count = candidates[0][0]
    best_method = candidates[0][1]
    best_waves = candidates[0][2]

    if best_count == 0:
        return None, None

    return (
        best_waves,
        best_method
    )


# ============================================================
# VALIDATE ONE QRS
# ============================================================

def validate_qrs(
    onset,
    r_peak,
    offset,
    signal_length,
    fs
):
    """
    Validate QRS onset / R peak / offset.

    Required geometry:

        onset < R peak < offset

    and duration must be within broad engineering limits.
    """

    onset = _clean_index(
        onset
    )

    r_peak = _clean_index(
        r_peak
    )

    offset = _clean_index(
        offset
    )

    if onset is None:
        return None

    if r_peak is None:
        return None

    if offset is None:
        return None

    if not (
        0 <= onset
        < r_peak
        < offset
        < signal_length
    ):
        return None

    duration_ms = (
        (offset - onset)
        / float(fs)
        * 1000.0
    )

    if not np.isfinite(
        duration_ms
    ):
        return None

    if not (
        MIN_QRS_MS
        <= duration_ms
        <= MAX_QRS_MS
    ):
        return None

    return {
        "onset": onset,
        "r_peak": r_peak,
        "offset": offset,
        "duration_ms": float(
            duration_ms
        )
    }


# ============================================================
# BEAT-LEVEL QRS EXTRACTION
# ============================================================

def extract_qrs_beats(
    cleaned_signal,
    r_peaks,
    waves,
    fs
):
    """
    Extract and validate beat-level QRS durations.
    """

    if waves is None:
        return []

    q_onsets = waves.get(
        "ECG_R_Onsets",
        []
    )

    q_offsets = waves.get(
        "ECG_R_Offsets",
        []
    )

    beats = []

    n = len(
        r_peaks
    )

    for i in range(n):

        r_peak = int(
            r_peaks[i]
        )

        onset = (
            q_onsets[i]
            if i < len(q_onsets)
            else None
        )

        offset = (
            q_offsets[i]
            if i < len(q_offsets)
            else None
        )

        validated = validate_qrs(
            onset,
            r_peak,
            offset,
            len(cleaned_signal),
            fs
        )

        if validated is None:
            continue

        validated[
            "beat_index"
        ] = i

        beats.append(
            validated
        )

    return beats


# ============================================================
# ROBUST QRS OUTLIER REJECTION
# ============================================================

def reject_qrs_outliers(
    beats
):
    """
    Reject beat-level QRS values that are grossly inconsistent
    with the patient's median.

    This does not change measured values.
    It only removes unreliable beats from the summary.
    """

    if len(beats) < 3:
        return beats

    durations = np.asarray(
        [
            beat["duration_ms"]
            for beat in beats
        ],
        dtype=float
    )

    median_qrs = np.median(
        durations
    )

    valid = []

    for beat in beats:

        duration = beat[
            "duration_ms"
        ]

        if (
            abs(
                duration
                - median_qrs
            )
            <= MAX_QRS_DEVIATION_MS
        ):
            valid.append(
                beat
            )

    return valid


# ============================================================
# HEART RATE
# ============================================================

def calculate_heart_rate(
    r_peaks,
    fs
):
    """
    Calculate robust heart rate from median valid RR interval.

    RR intervals outside the engineering limits are ignored.
    """

    if len(r_peaks) < 2:
        return np.nan

    rr_sec = (
        np.diff(r_peaks)
        / float(fs)
    )

    rr_sec = rr_sec[
        np.isfinite(rr_sec)
    ]

    rr_sec = rr_sec[
        (rr_sec >= MIN_RR_SEC)
        &
        (rr_sec <= MAX_RR_SEC)
    ]

    if len(rr_sec) == 0:
        return np.nan

    median_rr = np.median(
        rr_sec
    )

    if median_rr <= 0:
        return np.nan

    return float(
        60.0 / median_rr
    )


# ============================================================
# R-PEAK AMPLITUDE
# ============================================================

def calculate_r_amplitude(
    cleaned_signal,
    r_peaks
):
    """
    Calculate median R-peak amplitude.

    Returned value is in the signal's native units.

    It is only truly mV if the input signal has been
    calibrated to mV.
    """

    if len(r_peaks) == 0:
        return np.nan

    amplitudes = np.asarray(
        cleaned_signal[r_peaks],
        dtype=float
    )

    amplitudes = amplitudes[
        np.isfinite(amplitudes)
    ]

    if len(amplitudes) == 0:
        return np.nan

    return float(
        np.median(amplitudes)
    )


# ============================================================
# MAIN QRS ANALYSIS
# ============================================================

def analyze_qrs(
    cleaned_signal,
    fs
):
    """
    Analyze QRS morphology on the reference ECG lead.

    Returns
    -------
    result : dict
        Patient-level QRS parameters.

    r_peaks : np.ndarray
        Detected R-peak sample indices.
    """

    result = {

        "QRS_Duration_median_ms":
            np.nan,

        "QRS_Duration_mean_ms":
            np.nan,

        "QRS_Duration_std_ms":
            np.nan,

        "QRS_Valid_Beat_Count":
            0,

        "R_Peak_Count":
            0,

        "R_Amplitude_median":
            np.nan,

        "R_Amplitude_mean":
            np.nan,

        "Heart_Rate_bpm":
            np.nan,

        "QRS_QC_Status":
            "Not_available",

        # Do NOT claim DWT before actually selecting it.
        "QRS_Delineation_Method":
            np.nan,

        "QRS_Duration_min_ms":
            np.nan,

        "QRS_Duration_max_ms":
            np.nan,
    }

    r_peaks = np.array(
        [],
        dtype=int
    )

    # ========================================================
    # BASIC INPUT VALIDATION
    # ========================================================

    try:

        cleaned_signal = np.asarray(
            cleaned_signal,
            dtype=float
        )

        if cleaned_signal.ndim != 1:

            result[
                "QRS_QC_Status"
            ] = "Invalid_signal"

            return (
                result,
                r_peaks
            )

        if not np.isfinite(fs) or fs <= 0:

            result[
                "QRS_QC_Status"
            ] = "Invalid_sampling_rate"

            return (
                result,
                r_peaks
            )

        if len(cleaned_signal) < int(
            2 * fs
        ):

            result[
                "QRS_QC_Status"
            ] = "Signal_too_short"

            return (
                result,
                r_peaks
            )

        if not np.any(
            np.isfinite(cleaned_signal)
        ):

            result[
                "QRS_QC_Status"
            ] = "Invalid_signal"

            return (
                result,
                r_peaks
            )

    except Exception as e:

        print(
            f"  [qrs_module] "
            f"Input validation failed: {e}"
        )

        result[
            "QRS_QC_Status"
        ] = "Invalid_input"

        return (
            result,
            r_peaks
        )

    # ========================================================
    # R-PEAK DETECTION
    # ========================================================

    r_peaks = detect_r_peaks(
        cleaned_signal,
        fs
    )

    result[
        "R_Peak_Count"
    ] = int(
        len(r_peaks)
    )

    # ========================================================
    # PASS 1:
    # R AMPLITUDE ONLY NEEDS > 0 R PEAKS
    # ========================================================

    if len(r_peaks) == 0:

        result[
            "QRS_QC_Status"
        ] = "No_R_peaks"

        return (
            result,
            r_peaks
        )

    r_amplitude = calculate_r_amplitude(
        cleaned_signal,
        r_peaks
    )

    result[
        "R_Amplitude_median"
    ] = r_amplitude

    amplitude_values = np.asarray(
        cleaned_signal[r_peaks],
        dtype=float
    )

    amplitude_values = amplitude_values[
        np.isfinite(amplitude_values)
    ]

    if len(amplitude_values) > 0:

        result[
            "R_Amplitude_mean"
        ] = float(
            np.mean(
                amplitude_values
            )
        )

    # ========================================================
    # PASS 2:
    # HEART RATE NEEDS > 1 R PEAK
    # ========================================================

    result[
        "Heart_Rate_bpm"
    ] = calculate_heart_rate(
        r_peaks,
        fs
    )

    if len(r_peaks) < 2:

        result[
            "QRS_QC_Status"
        ] = (
            "Insufficient_R_peaks_for_QRS_duration"
        )

        return (
            result,
            r_peaks
        )

    # ========================================================
    # PASS 3:
    # QRS DELINEATION
    # ========================================================

    waves, method_used = delineate_qrs(
        cleaned_signal,
        r_peaks,
        fs
    )

    if waves is None:

        result[
            "QRS_QC_Status"
        ] = "Delineation_failed"

        return (
            result,
            r_peaks
        )

    result[
        "QRS_Delineation_Method"
    ] = method_used

    # ========================================================
    # EXTRACT BEAT-LEVEL QRS
    # ========================================================

    beats = extract_qrs_beats(
        cleaned_signal,
        r_peaks,
        waves,
        fs
    )

    if len(beats) == 0:

        result[
            "QRS_QC_Status"
        ] = "No_valid_QRS"

        return (
            result,
            r_peaks
        )

    # ========================================================
    # OUTLIER REJECTION
    # ========================================================

    original_valid_count = len(
        beats
    )

    beats = reject_qrs_outliers(
        beats
    )

    if len(beats) == 0:

        result[
            "QRS_QC_Status"
        ] = "All_QRS_rejected"

        return (
            result,
            r_peaks
        )

    result[
        "QRS_Valid_Beat_Count"
    ] = int(
        len(beats)
    )

    # ========================================================
    # QRS DURATION SUMMARY
    # ========================================================

    durations = np.asarray(
        [
            beat["duration_ms"]
            for beat in beats
        ],
        dtype=float
    )

    durations = durations[
        np.isfinite(durations)
    ]

    if len(durations) == 0:

        result[
            "QRS_QC_Status"
        ] = "No_finite_QRS"

        return (
            result,
            r_peaks
        )

    result[
        "QRS_Duration_median_ms"
    ] = float(
        np.median(durations)
    )

    result[
        "QRS_Duration_mean_ms"
    ] = float(
        np.mean(durations)
    )

    result[
        "QRS_Duration_std_ms"
    ] = float(
        np.std(durations)
    )

    result[
        "QRS_Duration_min_ms"
    ] = float(
        np.min(durations)
    )

    result[
        "QRS_Duration_max_ms"
    ] = float(
        np.max(durations)
    )

    # ========================================================
    # FINAL QC STATUS
    # ========================================================

    valid_fraction = (
        len(beats)
        / max(
            original_valid_count,
            1
        )
    )

    if len(beats) < MIN_VALID_QRS_BEATS:

        result[
            "QRS_QC_Status"
        ] = "Limited_valid_beats"

    elif valid_fraction < 0.50:

        result[
            "QRS_QC_Status"
        ] = "Poor_QRS_delineation"

    else:

        result[
            "QRS_QC_Status"
        ] = "Valid"

    return (
        result,
        r_peaks
    )