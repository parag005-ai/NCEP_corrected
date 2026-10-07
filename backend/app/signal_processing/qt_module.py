import numpy as np
import pandas as pd
import neurokit2 as nk


LEAD_ORDER = [
    "I",
    "II",
    "III",
    "AVR",
    "AVL",
    "AVF",
    "V1",
    "V2",
    "V3",
    "V4",
    "V5",
    "V6"
]


# ==========================================================
# TECHNICAL PLAUSIBILITY LIMITS
# ==========================================================

# These are software/data-quality guards.
# They are NOT clinical diagnosis cutoffs.

MIN_QT_S = 0.20
MAX_QT_S = 0.70

MIN_RR_S = 0.30
MAX_RR_S = 2.00


# ==========================================================
# QTc CALCULATION
# ==========================================================

def compute_qtc(
    qt,
    rr,
    method="bazett"
):
    """
    Calculate QTc.

    Parameters
    ----------
    qt : float
        QT interval in seconds.

    rr : float
        RR interval in seconds.

    method : str
        "bazett" or "fridericia"

    Returns
    -------
    float
        QTc in seconds, or NaN if invalid.
    """

    if (
        not np.isfinite(qt)
        or not np.isfinite(rr)
        or qt <= 0
        or rr <= 0
    ):
        return np.nan

    method = method.lower()

    if method == "bazett":

        return (
            qt
            / np.sqrt(rr)
        )

    elif method == "fridericia":

        return (
            qt
            / (rr ** (1.0 / 3.0))
        )

    else:

        raise ValueError(
            "Method should be "
            "'bazett' or 'fridericia'"
        )


# ==========================================================
# FALLBACK Q-START DETECTOR
# ==========================================================

def detect_q_start(
    cleaned_signal,
    r_peak,
    fs
):
    """
    Technical fallback detector for QRS onset.
    """

    search_window = int(
        0.08 * fs
    )

    start = max(
        1,
        r_peak - search_window
    )

    segment = cleaned_signal[
        start:r_peak
    ]

    if len(segment) < 10:
        return start

    zero_crossings = np.where(
        np.diff(
            np.sign(segment)
        )
    )[0]

    if len(zero_crossings) > 0:

        return (
            start
            + zero_crossings[-1]
        )

    derivative = np.gradient(
        segment
    )

    if len(derivative) == 0:
        return None

    slope_index = np.argmin(
        derivative
    )

    return (
        start
        + slope_index
    )


# ==========================================================
# FALLBACK T-ONSET DETECTOR
# ==========================================================

def detect_t_onset(
    cleaned_signal,
    t_peak,
    q_start,
    fs
):
    """
    Technical fallback detector for T-wave onset.

    The search is restricted to the interval between
    QRS onset and the T peak.
    """

    if q_start is None:
        return None

    if t_peak is None:
        return None

    if not (
        q_start < t_peak
    ):
        return None

    search_window = int(
        0.12 * fs
    )

    start = max(
        q_start,
        t_peak - search_window
    )

    segment = cleaned_signal[
        start:t_peak
    ]

    if len(segment) < 5:
        return None

    derivative = np.gradient(
        segment
    )

    maximum = np.max(
        np.abs(derivative)
    )

    if (
        not np.isfinite(maximum)
        or maximum == 0
    ):
        return None

    threshold = (
        0.02
        * maximum
    )

    for i in range(
        len(derivative) - 1,
        -1,
        -1
    ):

        if (
            abs(derivative[i])
            < threshold
        ):

            candidate = (
                start + i
            )

            if (
                q_start
                < candidate
                < t_peak
            ):
                return candidate

    return None


# ==========================================================
# FALLBACK T-OFFSET DETECTOR
# ==========================================================

def detect_t_offset(
    cleaned_signal,
    t_peak,
    next_r_peak,
    fs
):
    """
    Technical fallback detector for T-wave offset.

    Search is restricted to the interval between T peak
    and the next R peak.
    """

    if t_peak is None:
        return None

    if next_r_peak is None:
        return None

    if not (
        t_peak < next_r_peak
    ):
        return None

    search_window = int(
        0.18 * fs
    )

    end = min(
        next_r_peak,
        t_peak + search_window
    )

    segment = cleaned_signal[
        t_peak:end
    ]

    if len(segment) < 5:
        return None

    derivative = np.gradient(
        segment
    )

    maximum = np.max(
        np.abs(derivative)
    )

    if (
        not np.isfinite(maximum)
        or maximum == 0
    ):
        return None

    threshold = (
        0.02
        * maximum
    )

    for i in range(
        len(derivative)
    ):

        if (
            abs(derivative[i])
            < threshold
        ):

            candidate = (
                t_peak + i
            )

            if (
                t_peak
                < candidate
                < next_r_peak
            ):
                return candidate

    return None


# ==========================================================
# HELPERS
# ==========================================================

def clean_points(
    values,
    signal_length=None
):
    """
    Convert NeuroKit landmark values to integer sample indices
    while preserving unavailable values as NaN.
    """

    cleaned = []

    for value in values:

        if value is None:

            cleaned.append(
                np.nan
            )

            continue

        try:

            if pd.isna(value):

                cleaned.append(
                    np.nan
                )

                continue

            value = int(
                round(
                    float(value)
                )
            )

            if signal_length is not None:

                if not (
                    0 <= value
                    < signal_length
                ):

                    cleaned.append(
                        np.nan
                    )

                    continue

            cleaned.append(
                value
            )

        except Exception:

            cleaned.append(
                np.nan
            )

    return cleaned


def _safe_index(
    value,
    signal_length
):
    """
    Convert a point to a valid sample index.
    """

    if value is None:
        return None

    try:

        if pd.isna(value):
            return None

        value = int(
            round(
                float(value)
            )
        )

    except Exception:

        return None

    if not (
        0 <= value
        < signal_length
    ):
        return None

    return value


def first_valid_in_window(
    values,
    start_point,
    end_point
):
    """
    Return first valid point strictly inside the window.
    """

    if start_point is None:
        return None

    if end_point is None:
        return None

    for value in values:

        if pd.isna(value):
            continue

        try:

            value = int(value)

        except Exception:

            continue

        if (
            start_point
            < value
            < end_point
        ):

            return value

    return None


def last_valid_in_window(
    values,
    start_point,
    end_point
):
    """
    Return last valid point strictly inside the window.
    """

    if start_point is None:
        return None

    if end_point is None:
        return None

    last_value = None

    for value in values:

        if pd.isna(value):
            continue

        try:

            value = int(value)

        except Exception:

            continue

        if (
            start_point
            < value
            < end_point
        ):

            last_value = value

    return last_value


# ==========================================================
# QT LANDMARK VALIDATION
# ==========================================================

def validate_qt_landmarks(
    q_start,
    r_peak,
    t_peak,
    t_onset,
    t_offset,
    next_r_peak,
    signal_length
):
    """
    Validate QT landmark geometry.

    Required ordering:

        Q-start
        <
        R peak
        <
        T onset
        <
        T peak
        <
        T offset
        <
        next R

    All landmarks must remain inside the signal.
    """

    values = [
        q_start,
        r_peak,
        t_onset,
        t_peak,
        t_offset,
        next_r_peak
    ]

    for value in values:

        if value is None:
            return False

        try:

            if not np.isfinite(value):
                return False

        except Exception:

            return False

    if not (
        0 <= q_start
        < r_peak
        < t_onset
        < t_peak
        < t_offset
        < next_r_peak
        < signal_length
    ):
        return False

    return True


# ==========================================================
# CHOOSE BEST DELINEATION
# ==========================================================

def choose_best_delineation(
    cleaned_signal,
    r_peaks,
    fs
):
    """
    Try both prominence and DWT delineation.

    Select the method producing the largest number of
    complete, technically valid QT beats.

    A beat is valid only when:

        Q-start < R-peak < T-onset
        < T-peak < T-offset < next R

    and QT/RR satisfy the technical limits.
    """

    best_waves = None
    best_method = None
    best_score = -1

    for method in [
        "prominence",
        "dwt"
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

            signal_length = len(
                cleaned_signal
            )

            r_onsets = clean_points(
                waves.get(
                    "ECG_R_Onsets",
                    []
                ),
                signal_length
            )

            t_peaks = clean_points(
                waves.get(
                    "ECG_T_Peaks",
                    []
                ),
                signal_length
            )

            t_onsets = clean_points(
                waves.get(
                    "ECG_T_Onsets",
                    []
                ),
                signal_length
            )

            t_offsets = clean_points(
                waves.get(
                    "ECG_T_Offsets",
                    []
                ),
                signal_length
            )

            valid_beats = 0

            for i in range(
                len(r_peaks) - 1
            ):

                r_peak = int(
                    r_peaks[i]
                )

                next_r_peak = int(
                    r_peaks[i + 1]
                )

                # ------------------------------------------
                # Q START
                # ------------------------------------------

                q_start = None

                if (
                    i < len(r_onsets)
                    and not pd.isna(
                        r_onsets[i]
                    )
                ):

                    q_start = _safe_index(
                        r_onsets[i],
                        signal_length
                    )

                if q_start is None:

                    q_start = detect_q_start(
                        cleaned_signal,
                        r_peak,
                        fs
                    )

                if q_start is None:
                    continue

                # ------------------------------------------
                # T PEAK
                # ------------------------------------------

                t_peak = None

                if (
                    i < len(t_peaks)
                    and not pd.isna(
                        t_peaks[i]
                    )
                ):

                    candidate = _safe_index(
                        t_peaks[i],
                        signal_length
                    )

                    if (
                        candidate is not None
                        and r_peak
                        < candidate
                        < next_r_peak
                    ):

                        t_peak = candidate

                if t_peak is None:
                    continue

                # ------------------------------------------
                # T ONSET
                # ------------------------------------------

                t_onset = None

                if (
                    i < len(t_onsets)
                    and not pd.isna(
                        t_onsets[i]
                    )
                ):

                    candidate = _safe_index(
                        t_onsets[i],
                        signal_length
                    )

                    if (
                        candidate is not None
                        and q_start
                        < candidate
                        < t_peak
                    ):

                        t_onset = candidate

                if t_onset is None:

                    t_onset = detect_t_onset(
                        cleaned_signal,
                        t_peak,
                        q_start,
                        fs
                    )

                if t_onset is None:
                    continue

                # ------------------------------------------
                # T OFFSET
                # ------------------------------------------

                t_offset = None

                if (
                    i < len(t_offsets)
                    and not pd.isna(
                        t_offsets[i]
                    )
                ):

                    candidate = _safe_index(
                        t_offsets[i],
                        signal_length
                    )

                    if (
                        candidate is not None
                        and t_peak
                        < candidate
                        < next_r_peak
                    ):

                        t_offset = candidate

                if t_offset is None:

                    t_offset = detect_t_offset(
                        cleaned_signal,
                        t_peak,
                        next_r_peak,
                        fs
                    )

                if t_offset is None:
                    continue

                # ------------------------------------------
                # LANDMARK VALIDATION
                # ------------------------------------------

                if not validate_qt_landmarks(
                    q_start,
                    r_peak,
                    t_peak,
                    t_onset,
                    t_offset,
                    next_r_peak,
                    signal_length
                ):
                    continue

                # ------------------------------------------
                # QT / RR
                # ------------------------------------------

                qt = (
                    t_offset
                    - q_start
                ) / float(fs)

                rr = (
                    next_r_peak
                    - r_peak
                ) / float(fs)

                if not (
                    np.isfinite(qt)
                    and np.isfinite(rr)
                    and qt > 0
                    and rr > 0
                ):
                    continue

                # ------------------------------------------
                # QT TECHNICAL GUARD
                # ------------------------------------------

                if not (
                    MIN_QT_S
                    <= qt
                    <= MAX_QT_S
                ):
                    continue

                # ------------------------------------------
                # RR TECHNICAL GUARD
                # ------------------------------------------

                if not (
                    MIN_RR_S
                    <= rr
                    <= MAX_RR_S
                ):
                    continue

                # ------------------------------------------
                # QTc VALIDATION
                # ------------------------------------------

                qtc_bazett = compute_qtc(
                    qt,
                    rr,
                    "bazett"
                )

                qtc_fridericia = compute_qtc(
                    qt,
                    rr,
                    "fridericia"
                )

                if not (
                    np.isfinite(qtc_bazett)
                    and qtc_bazett > 0
                ):
                    continue

                if not (
                    np.isfinite(qtc_fridericia)
                    and qtc_fridericia > 0
                ):
                    continue

                # ------------------------------------------
                # TPE VALIDATION
                # ------------------------------------------

                tpe = (
                    t_offset
                    - t_peak
                ) / float(fs)

                if not (
                    np.isfinite(tpe)
                    and tpe > 0
                ):
                    continue

                valid_beats += 1

            print(
                f"  [qt_module] "
                f"{method}: "
                f"{valid_beats} valid QT beats"
            )

            if valid_beats > best_score:

                best_score = valid_beats
                best_waves = waves
                best_method = method

        except Exception as e:

            print(
                f"  [qt_module] "
                f"{method} delineation failed: {e}"
            )

    if best_score <= 0:

        return (
            None,
            None
        )

    return (
        best_waves,
        best_method
    )


# ==========================================================
# ANALYZE ONE LEAD
# ==========================================================

def _analyze_lead(
    cleaned_signal,
    fs,
    lead_name="UNKNOWN",
    debug=False
):
    """
    Analyze QT/QTc measurements for one ECG lead.
    """

    try:

        _, peak_info = nk.ecg_peaks(
            cleaned_signal,
            sampling_rate=fs,
            method="neurokit"
        )

        r_peaks = np.asarray(
            peak_info.get(
                "ECG_R_Peaks",
                []
            ),
            dtype=int
        )

        r_peaks = r_peaks[
            (r_peaks >= 0)
            &
            (r_peaks < len(cleaned_signal))
        ]

        r_peaks = np.unique(
            r_peaks
        )

        if debug:

            print(
                f"  [QT DEBUG] "
                f"Lead={lead_name}: "
                f"R-peaks detected="
                f"{len(r_peaks)}"
            )

    except Exception as e:

        if debug:

            print(
                f"  [QT DEBUG] "
                f"Lead={lead_name}: "
                f"R-peak detection failed: "
                f"{e}"
            )

        return None

    if len(r_peaks) < 2:
        return None

    waves, method_used = choose_best_delineation(
        cleaned_signal,
        r_peaks,
        fs
    )

    if waves is None:
        return None

    signal_length = len(
        cleaned_signal
    )

    r_onsets = clean_points(
        waves.get(
            "ECG_R_Onsets",
            []
        ),
        signal_length
    )

    t_peaks = clean_points(
        waves.get(
            "ECG_T_Peaks",
            []
        ),
        signal_length
    )

    t_onsets_raw = clean_points(
        waves.get(
            "ECG_T_Onsets",
            []
        ),
        signal_length
    )

    t_offsets_raw = clean_points(
        waves.get(
            "ECG_T_Offsets",
            []
        ),
        signal_length
    )

    qt_values = []
    rr_values = []

    bazett_values = []
    fridericia_values = []

    tpe_values = []
    tpe_qt_ratios = []

    # ======================================================
    # BEAT LOOP
    # ======================================================

    for i in range(
        len(r_peaks) - 1
    ):

        r_peak = int(
            r_peaks[i]
        )

        next_r_peak = int(
            r_peaks[i + 1]
        )

        # ==================================================
        # Q START
        # ==================================================

        q_start = None

        if (
            i < len(r_onsets)
            and not pd.isna(
                r_onsets[i]
            )
        ):

            q_start = _safe_index(
                r_onsets[i],
                signal_length
            )

        if q_start is None:

            q_start = detect_q_start(
                cleaned_signal,
                r_peak,
                fs
            )

        if q_start is None:
            continue

        # ==================================================
        # T PEAK
        # ==================================================

        t_peak = None

        if (
            i < len(t_peaks)
            and not pd.isna(
                t_peaks[i]
            )
        ):

            candidate = _safe_index(
                t_peaks[i],
                signal_length
            )

            if (
                candidate is not None
                and r_peak
                < candidate
                < next_r_peak
            ):

                t_peak = candidate

        if t_peak is None:
            continue

        # ==================================================
        # T ONSET
        # ==================================================

        t_onset = None

        if (
            i < len(t_onsets_raw)
            and not pd.isna(
                t_onsets_raw[i]
            )
        ):

            candidate = _safe_index(
                t_onsets_raw[i],
                signal_length
            )

            if (
                candidate is not None
                and q_start
                < candidate
                < t_peak
            ):

                t_onset = candidate

        if t_onset is None:

            t_onset = detect_t_onset(
                cleaned_signal,
                t_peak,
                q_start,
                fs
            )

        if t_onset is None:
            continue

        # ==================================================
        # T OFFSET
        # ==================================================

        t_offset = None

        if (
            i < len(t_offsets_raw)
            and not pd.isna(
                t_offsets_raw[i]
            )
        ):

            candidate = _safe_index(
                t_offsets_raw[i],
                signal_length
            )

            if (
                candidate is not None
                and t_peak
                < candidate
                < next_r_peak
            ):

                t_offset = candidate

        if t_offset is None:

            t_offset = detect_t_offset(
                cleaned_signal,
                t_peak,
                next_r_peak,
                fs
            )

        if t_offset is None:
            continue

        # ==================================================
        # COMPLETE LANDMARK VALIDATION
        # ==================================================

        if not validate_qt_landmarks(
            q_start,
            r_peak,
            t_peak,
            t_onset,
            t_offset,
            next_r_peak,
            signal_length
        ):
            continue

        # ==================================================
        # QT / RR
        # ==================================================

        qt = (
            t_offset
            - q_start
        ) / float(fs)

        rr = (
            next_r_peak
            - r_peak
        ) / float(fs)

        if not (
            np.isfinite(qt)
            and np.isfinite(rr)
            and qt > 0
            and rr > 0
        ):
            continue

        if debug:

            print(
                f"  [QT DEBUG] "
                f"Lead={lead_name} "
                f"beat={i}: "
                f"Q={q_start}, "
                f"R={r_peak}, "
                f"T_on={t_onset}, "
                f"T={t_peak}, "
                f"T_off={t_offset}, "
                f"QT={qt * 1000:.1f} ms, "
                f"RR={rr * 1000:.1f} ms"
            )

        # ==================================================
        # QT TECHNICAL PLAUSIBILITY
        # ==================================================

        if not (
            MIN_QT_S
            <= qt
            <= MAX_QT_S
        ):

            if debug:

                print(
                    f"  [QT REJECT] "
                    f"Lead={lead_name} "
                    f"beat={i}: "
                    f"QT={qt * 1000:.1f} ms "
                    f"outside "
                    f"{MIN_QT_S * 1000:.0f}-"
                    f"{MAX_QT_S * 1000:.0f} ms"
                )

            continue

        # ==================================================
        # RR TECHNICAL PLAUSIBILITY
        # ==================================================

        if not (
            MIN_RR_S
            <= rr
            <= MAX_RR_S
        ):

            if debug:

                print(
                    f"  [RR REJECT] "
                    f"Lead={lead_name} "
                    f"beat={i}: "
                    f"RR={rr * 1000:.1f} ms "
                    f"outside "
                    f"{MIN_RR_S * 1000:.0f}-"
                    f"{MAX_RR_S * 1000:.0f} ms"
                )

            continue

        # ==================================================
        # QTc
        # ==================================================

        qtc_bazett = compute_qtc(
            qt,
            rr,
            "bazett"
        )

        qtc_fridericia = compute_qtc(
            qt,
            rr,
            "fridericia"
        )

        if not (
            np.isfinite(qtc_bazett)
            and qtc_bazett > 0
        ):

            if debug:

                print(
                    f"  [QT REJECT] "
                    f"Lead={lead_name} "
                    f"beat={i}: "
                    f"invalid Bazett QTc"
                )

            continue

        if not (
            np.isfinite(qtc_fridericia)
            and qtc_fridericia > 0
        ):

            if debug:

                print(
                    f"  [QT REJECT] "
                    f"Lead={lead_name} "
                    f"beat={i}: "
                    f"invalid Fridericia QTc"
                )

            continue

        # ==================================================
        # TPE
        # ==================================================

        tpe = (
            t_offset
            - t_peak
        ) / float(fs)

        if not (
            np.isfinite(tpe)
            and tpe > 0
        ):

            if debug:

                print(
                    f"  [QT REJECT] "
                    f"Lead={lead_name} "
                    f"beat={i}: "
                    f"invalid Tpe"
                )

            continue

        # ==================================================
        # TPE / QT RATIO
        # ==================================================

        tpe_qt_ratio = (
            tpe / qt
            if qt > 0
            else np.nan
        )

        if not (
            np.isfinite(
                tpe_qt_ratio
            )
            and tpe_qt_ratio > 0
        ):

            if debug:

                print(
                    f"  [QT REJECT] "
                    f"Lead={lead_name} "
                    f"beat={i}: "
                    f"invalid Tpe/QT ratio"
                )

            continue

        # ==================================================
        # ACCEPTED BEAT
        # ==================================================

        qt_ms = (
            qt
            * 1000.0
        )

        rr_ms = (
            rr
            * 1000.0
        )

        qtc_bazett_ms = (
            qtc_bazett
            * 1000.0
        )

        qtc_fridericia_ms = (
            qtc_fridericia
            * 1000.0
        )

        tpe_ms = (
            tpe
            * 1000.0
        )

        qt_values.append(
            qt_ms
        )

        rr_values.append(
            rr_ms
        )

        bazett_values.append(
            qtc_bazett_ms
        )

        fridericia_values.append(
            qtc_fridericia_ms
        )

        tpe_values.append(
            tpe_ms
        )

        tpe_qt_ratios.append(
            tpe_qt_ratio
        )

    # ======================================================
    # NO VALID QT BEATS
    # ======================================================

    if len(qt_values) == 0:
        return None

    return {
        "qt":
            qt_values,

        "rr":
            rr_values,

        "bazett":
            bazett_values,

        "fridericia":
            fridericia_values,

        "tpe":
            tpe_values,

        "tpe_qt_ratio":
            tpe_qt_ratios,

        "method":
            method_used,
    }


# ==========================================================
# ANALYZE ALL LEADS
# ==========================================================

def analyze_qt(
    cleaned_leads,
    fs,
    debug=False
):
    """
    Analyze QT/QTc measurements across all 12 ECG leads.

    Returns
    -------
    dict
        Patient-level QT/QTc results.
    """

    result = {}

    all_qt_values_across_leads = []
    all_tpe_values_across_leads = []

    for lead in LEAD_ORDER:

        lead_upper = lead.upper()

        signal = cleaned_leads.get(
            lead
        )

        cols = {

            f"Avg_QT_{lead_upper}_ms":
                np.nan,

            f"Avg_RR_{lead_upper}_ms":
                np.nan,

            f"Avg_QTc_Bazett_{lead_upper}_ms":
                np.nan,

            f"Avg_QTc_Fridericia_{lead_upper}_ms":
                np.nan,

            f"Beats_{lead_upper}":
                np.nan,

            f"Avg_Tpe_{lead_upper}_ms":
                np.nan,

            f"Avg_Tpe_Qt_ratio_{lead_upper}":
                np.nan,

            f"QT_max_{lead_upper}_ms":
                np.nan,

            f"QT_min_{lead_upper}_ms":
                np.nan,

            f"QT_disp_{lead_upper}_ms":
                np.nan,
        }

        if signal is not None:

            try:

                lead_data = _analyze_lead(
                    signal,
                    fs,
                    lead_name=lead,
                    debug=debug
                )

            except Exception as e:

                print(
                    f"  [qt_module] "
                    f"Lead {lead} failed: {e}"
                )

                lead_data = None

            if lead_data is not None:

                qt_values = lead_data[
                    "qt"
                ]

                rr_values = lead_data[
                    "rr"
                ]

                bazett_values = lead_data[
                    "bazett"
                ]

                fridericia_values = lead_data[
                    "fridericia"
                ]

                tpe_values = lead_data[
                    "tpe"
                ]

                ratio_values = lead_data[
                    "tpe_qt_ratio"
                ]

                if len(qt_values) > 0:

                    cols[
                        f"Avg_QT_{lead_upper}_ms"
                    ] = float(
                        np.mean(
                            qt_values
                        )
                    )

                    cols[
                        f"Avg_RR_{lead_upper}_ms"
                    ] = float(
                        np.mean(
                            rr_values
                        )
                    )

                    cols[
                        f"Avg_QTc_Bazett_{lead_upper}_ms"
                    ] = float(
                        np.mean(
                            bazett_values
                        )
                    )

                    cols[
                        f"Avg_QTc_Fridericia_{lead_upper}_ms"
                    ] = float(
                        np.mean(
                            fridericia_values
                        )
                    )

                    cols[
                        f"Beats_{lead_upper}"
                    ] = int(
                        len(qt_values)
                    )

                    cols[
                        f"Avg_Tpe_{lead_upper}_ms"
                    ] = float(
                        np.mean(
                            tpe_values
                        )
                    )

                    if ratio_values:

                        cols[
                            f"Avg_Tpe_Qt_ratio_{lead_upper}"
                        ] = float(
                            np.mean(
                                ratio_values
                            )
                        )

                    cols[
                        f"QT_max_{lead_upper}_ms"
                    ] = float(
                        np.max(
                            qt_values
                        )
                    )

                    cols[
                        f"QT_min_{lead_upper}_ms"
                    ] = float(
                        np.min(
                            qt_values
                        )
                    )

                    cols[
                        f"QT_disp_{lead_upper}_ms"
                    ] = float(
                        np.max(
                            qt_values
                        )
                        -
                        np.min(
                            qt_values
                        )
                    )

                    all_qt_values_across_leads.extend(
                        qt_values
                    )

                    all_tpe_values_across_leads.extend(
                        tpe_values
                    )

        result.update(
            cols
        )

    # ==========================================================
    # FINAL QT INVARIANT
    # ==========================================================

    for lead in LEAD_ORDER:

        max_col = (
            f"QT_max_{lead}_ms"
        )

        min_col = (
            f"QT_min_{lead}_ms"
        )

        if (
            max_col in result
            and pd.notna(
                result[max_col]
            )
        ):

            if (
                result[max_col]
                > MAX_QT_S * 1000.0
            ):

                raise RuntimeError(
                    f"QT invariant failed "
                    f"for lead {lead}: "
                    f"QT_max="
                    f"{result[max_col]:.1f} ms"
                )

        if (
            min_col in result
            and pd.notna(
                result[min_col]
            )
        ):

            if (
                result[min_col]
                < MIN_QT_S * 1000.0
            ):

                raise RuntimeError(
                    f"QT invariant failed "
                    f"for lead {lead}: "
                    f"QT_min="
                    f"{result[min_col]:.1f} ms"
                )

    # ==========================================================
    # GLOBAL QT DISPERSION
    # ==========================================================

    if all_qt_values_across_leads:

        result[
            "QT_max_global_ms"
        ] = float(
            np.max(
                all_qt_values_across_leads
            )
        )

        result[
            "QT_min_global_ms"
        ] = float(
            np.min(
                all_qt_values_across_leads
            )
        )

        result[
            "QT_dispersion_global_ms"
        ] = float(
            result[
                "QT_max_global_ms"
            ]
            -
            result[
                "QT_min_global_ms"
            ]
        )

    else:

        result[
            "QT_max_global_ms"
        ] = np.nan

        result[
            "QT_min_global_ms"
        ] = np.nan

        result[
            "QT_dispersion_global_ms"
        ] = np.nan

    # ==========================================================
    # GLOBAL TPE / QT RATIO
    # ==========================================================

    if (
        all_qt_values_across_leads
        and all_tpe_values_across_leads
    ):

        global_ratios = []

        for qt, tpe in zip(
            all_qt_values_across_leads,
            all_tpe_values_across_leads
        ):

            if (
                np.isfinite(qt)
                and np.isfinite(tpe)
                and qt > 0
                and tpe > 0
            ):

                global_ratios.append(
                    tpe / qt
                )

        if global_ratios:

            result[
                "Avg_Tpe_Qt_ratio_GLOBAL"
            ] = float(
                np.mean(
                    global_ratios
                )
            )

        else:

            result[
                "Avg_Tpe_Qt_ratio_GLOBAL"
            ] = np.nan

    else:

        result[
            "Avg_Tpe_Qt_ratio_GLOBAL"
        ] = np.nan

    return result