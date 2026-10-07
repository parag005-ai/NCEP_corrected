"""
p_saecg_module.py
==================
Adapted from build_p_saecg_batch2.py (P-SAECG waveform averaging) and
atrial_lp_metrics.py (Atrial Late Potential metrics: FPD, RMS20, LAS20).

WHAT THIS COMPUTES (on the reference lead):
    - P-SAECG: averages every detected P-wave segment into one
      representative waveform, with an SNR estimate
    - Filtered P Duration (FPD, ms): duration of the averaged waveform
      above a noise threshold
    - RMS20: RMS amplitude of the last 20ms of the averaged P-wave
    - LAS20 (ms): low-amplitude signal duration in that terminal segment
      (early marker of atrial conduction abnormality / risk of AFib)

CHANGED FROM ORIGINALS:
    - No longer loads/cleans signals or re-detects R-peaks itself --
      takes the already-cleaned reference lead signal and the R-peaks
      already found by qrs_module.py, so peak detection isn't repeated.
    - No longer saves its own CSV/PNG files -- returns one dict per
      patient, same pattern as the other modules.
"""

import numpy as np
import neurokit2 as nk


# ==========================================================
# BUILD P-SAECG (from build_p_saecg_batch2.py)
# ==========================================================

def build_p_saecg(cleaned_signal, r_peaks, fs):
    """
    Returns (psaecg_waveform, snr_db, beats_used).
    psaecg_waveform is None if no valid P-waves were found.
    """
    if r_peaks is None or len(r_peaks) == 0:
        return None, np.nan, 0

    try:
        _, waves = nk.ecg_delineate(
            cleaned_signal,
            r_peaks,
            sampling_rate=fs,
            method="dwt"
        )

        p_onsets = waves.get("ECG_P_Onsets", [])
        p_offsets = waves.get("ECG_P_Offsets", [])

        segments = []
        for onset, offset in zip(p_onsets, p_offsets):
            if onset is None or offset is None:
                continue
            if np.isnan(onset) or np.isnan(offset):
                continue

            onset, offset = int(onset), int(offset)
            segment = cleaned_signal[onset:offset]

            if len(segment) > 5:
                segments.append(segment)

        if len(segments) == 0:
            return None, np.nan, 0

        min_length = min(len(s) for s in segments)
        trimmed = [s[:min_length] for s in segments]

        psaecg = np.mean(trimmed, axis=0)

        signal_power = np.mean(psaecg ** 2)
        noise = np.array(trimmed) - psaecg
        noise_power = np.mean(noise ** 2)
        snr = 10 * np.log10(signal_power / (noise_power + 1e-12))

        return psaecg, float(snr), len(trimmed)

    except Exception as e:
        print(f"  [p_saecg_module] build_p_saecg failed: {e}")
        return None, np.nan, 0


# ==========================================================
# ATRIAL LATE POTENTIAL METRICS (from atrial_lp_metrics.py)
# ==========================================================

def compute_atrial_lp_metrics(p_saecg_waveform, fs):
    """Returns dict with Filtered P Duration, RMS20, LAS20."""

    empty_result = {
        "Filtered_P_Duration_ms": np.nan,
        "RMS20_mV": np.nan,
        "LAS20_ms": np.nan,
    }

    if p_saecg_waveform is None:
        return empty_result

    waveform = np.asarray(p_saecg_waveform)
    if len(waveform) == 0:
        return empty_result

    waveform = waveform - np.mean(waveform)

    threshold = 0.02 * np.max(np.abs(waveform))
    indices = np.where(np.abs(waveform) > threshold)[0]

    if len(indices) == 0:
        return {"Filtered_P_Duration_ms": 0.0, "RMS20_mV": 0.0, "LAS20_ms": 0.0}

    onset = indices[0]
    offset = indices[-1]

    fpd = (offset - onset) / fs * 1000

    samples20 = int(0.020 * fs)
    end_segment = waveform[max(0, offset - samples20 + 1): offset + 1]

    rms20 = np.sqrt(np.mean(end_segment ** 2))

    peak_amplitude = np.max(np.abs(end_segment))
    threshold20 = peak_amplitude * 0.20
    below = np.abs(end_segment) < threshold20
    las20 = (np.sum(below) / fs) * 1000

    return {
        "Filtered_P_Duration_ms": round(float(fpd), 2),
        "RMS20_mV": round(float(rms20), 6),
        "LAS20_ms": round(float(las20), 2),
    }


# ==========================================================
# COMBINED ANALYSIS (called by the orchestrator)
# ==========================================================

def analyze_p_saecg(cleaned_signal, r_peaks, fs):
    """
    cleaned_signal : reference lead's cleaned signal
    r_peaks        : R-peaks already detected by qrs_module.py
    fs             : sampling rate

    Returns a dict of patient-level P-SAECG + Atrial LP parameters.
    """
    psaecg, snr, beats_used = build_p_saecg(cleaned_signal, r_peaks, fs)
    lp_metrics = compute_atrial_lp_metrics(psaecg, fs)

    result = {
        "P_SAECG_SNR_dB": snr if not np.isnan(snr) else np.nan,
        "P_SAECG_Beats_Used": beats_used,
    }
    result.update(lp_metrics)

    return result
