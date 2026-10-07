"""
t_wave_module.py
=================
Adapted from task4_1.py.

CHANGED FROM ORIGINAL:
  - No longer loads or cleans signals itself -- receives the already
    cleaned leads from preprocessing.py.
  - No longer re-detects R-peaks per lead -- reuses the SAME r_peaks
    that qrs_module.py already found on the reference lead, so peak
    detection only happens once per patient.
  - Original produced one row PER BEAT PER LEAD. This version averages
    each lead's T-wave duration (and late potential metrics) across all
    its beats, so each patient contributes exactly one row's worth of
    columns:
        T_Duration_<LEAD>_ms       (one column per available lead)
        T_Late_RMS_<LEAD>_mV       (late potential RMS, averaged)
        T_Late_PTP_<LEAD>_mV       (late potential peak-to-peak, averaged)
        T_Late_Flag_Rate_<LEAD>    (fraction of beats flagged as late potential)
        T_Wave_Dispersion_ms       (max lead avg - min lead avg)
  - Keeps the same 80-250ms physiological plausibility filter, and the
    same late-potential detection window/thresholds, that the original
    used.
"""

import numpy as np
import neurokit2 as nk


# ==========================================================
# T-WAVE LATE POTENTIAL METRICS (from task4_1.py, unchanged logic)
# ==========================================================

def detect_t_wave_late_signals(ecg, t_on, t_off, fs):
    late_window = int(0.04 * fs)
    start = max(t_on, t_off - late_window)
    end = t_off

    segment = ecg[start:end]
    if len(segment) < 5:
        return None

    segment = segment - np.mean(segment)
    rms = np.sqrt(np.mean(segment ** 2))
    ptp = np.ptp(segment)

    return {"rms": rms, "ptp": ptp}


def compute_t_wave_lp_metrics(late_signal):
    if late_signal is None:
        return None

    rms = late_signal["rms"]
    ptp = late_signal["ptp"]
    flag = (rms < 0.02) and (ptp < 0.05)

    return rms, ptp, flag


def analyze_twave(cleaned_leads, r_peaks, fs):
    """
    cleaned_leads : dict {lead_name: cleaned_signal}, from preprocessing.py
    r_peaks       : np.ndarray of R-peak indices (from qrs_module.py,
                     detected on the reference lead)
    fs            : sampling rate

    Returns a dict of patient-level T-wave parameters.
    """
    result = {}
    lead_stats = {}

    if r_peaks is None or len(r_peaks) == 0:
        # No peaks -> nothing to delineate; return NaNs for every lead
        for lead in cleaned_leads:
            result[f"T_Duration_{lead}_ms"] = np.nan
            result[f"T_Late_RMS_{lead}_mV"] = np.nan
            result[f"T_Late_PTP_{lead}_mV"] = np.nan
            result[f"T_Late_Flag_Rate_{lead}"] = np.nan
        result["T_Wave_Dispersion_ms"] = np.nan
        return result

    for lead, signal in cleaned_leads.items():
        if signal is None:
            lead_stats[lead] = {"duration": np.nan, "rms": np.nan, "ptp": np.nan, "flag_rate": np.nan}
            continue

        try:
            _, waves = nk.ecg_delineate(
                signal,
                {"ECG_R_Peaks": r_peaks},
                sampling_rate=fs,
                method="dwt"
            )

            t_onsets = waves.get("ECG_T_Onsets", [])
            t_offsets = waves.get("ECG_T_Offsets", [])

            durations = []
            rms_values = []
            ptp_values = []
            flags = []

            for t_on, t_off in zip(t_onsets, t_offsets):
                if t_on is None or t_off is None:
                    continue
                if np.isnan(t_on) or np.isnan(t_off):
                    continue
                if t_off <= t_on:
                    continue

                t_on_i, t_off_i = int(t_on), int(t_off)
                duration_ms = (t_off_i - t_on_i) * 1000 / fs

                # Same physiological plausibility filter as task4_1.py
                if not (80 <= duration_ms <= 250):
                    continue
                durations.append(duration_ms)

                # Late potential metrics for this beat
                late_signal = detect_t_wave_late_signals(signal, t_on_i, t_off_i, fs)
                metrics = compute_t_wave_lp_metrics(late_signal)
                if metrics is not None:
                    rms, ptp, flag = metrics
                    rms_values.append(rms)
                    ptp_values.append(ptp)
                    flags.append(flag)

            lead_stats[lead] = {
                "duration": float(np.mean(durations)) if durations else np.nan,
                "rms": float(np.mean(rms_values)) if rms_values else np.nan,
                "ptp": float(np.mean(ptp_values)) if ptp_values else np.nan,
                "flag_rate": float(np.mean(flags)) if flags else np.nan,
            }

        except Exception as e:
            print(f"  [t_wave_module] Lead {lead} failed: {e}")
            lead_stats[lead] = {"duration": np.nan, "rms": np.nan, "ptp": np.nan, "flag_rate": np.nan}

    for lead, stats in lead_stats.items():
        result[f"T_Duration_{lead}_ms"] = stats["duration"]
        result[f"T_Late_RMS_{lead}_mV"] = stats["rms"]
        result[f"T_Late_PTP_{lead}_mV"] = stats["ptp"]
        result[f"T_Late_Flag_Rate_{lead}"] = stats["flag_rate"]

    valid_durations = [s["duration"] for s in lead_stats.values() if not np.isnan(s["duration"])]
    if len(valid_durations) >= 2:
        result["T_Wave_Dispersion_ms"] = float(max(valid_durations) - min(valid_durations))
    else:
        result["T_Wave_Dispersion_ms"] = np.nan

    return result
