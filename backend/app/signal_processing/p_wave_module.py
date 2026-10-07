"""
p_wave_module.py
=================
Adapted from all_patients_pwave_batch2.py (single-lead P-wave duration)
PLUS p_wave_duration_per_lead_batch2.py and pwave_dispersion_summary.py
(per-lead P-wave duration + P-Wave Dispersion).

CHANGED FROM ORIGINALS:
  - No longer loads or cleans signals itself -- receives the already
    cleaned leads from preprocessing.py.
  - Instead of one CSV per patient (or per patient-per-lead), returns a
    single aggregated dict per patient:
        P_Duration_<LEAD>_ms   (one column per available lead)
        P_Wave_Dispersion_ms   (max lead avg - min lead avg)
        P_Duration_mean_ms / P_Duration_std_ms / P_Wave_Count
              (kept for backwards compatibility -- same numbers as
              before, computed on the reference lead only)
"""

import numpy as np
import neurokit2 as nk


def _analyze_lead_pwave(cleaned_signal, fs):
    """Returns list of P-wave durations (ms) for ONE lead, or None if it fails."""
    try:
        _, info = nk.ecg_peaks(cleaned_signal, sampling_rate=fs)
        r_peaks = info["ECG_R_Peaks"]

        if len(r_peaks) < 3:
            return None

        _, waves = nk.ecg_delineate(
            cleaned_signal,
            r_peaks,
            sampling_rate=fs,
            method="dwt"
        )

        p_onsets = waves.get("ECG_P_Onsets", [])
        p_offsets = waves.get("ECG_P_Offsets", [])

        durations = []
        for onset, offset in zip(p_onsets, p_offsets):
            if onset is None or offset is None:
                continue
            if np.isnan(onset) or np.isnan(offset):
                continue
            durations.append((offset - onset) / fs * 1000)

        return durations if durations else None

    except Exception:
        return None


def analyze_pwave(cleaned_leads, reference_lead, fs):
    """
    cleaned_leads   : dict {lead_name: cleaned_signal}, from preprocessing.py
    reference_lead  : the lead name used for the backwards-compatible
                       P_Duration_mean_ms / std / count columns
    fs              : sampling rate

    Returns a dict of patient-level P-wave parameters (per lead + global).
    """
    result = {}
    lead_means = {}

    for lead, signal in cleaned_leads.items():
        if signal is None:
            lead_means[lead] = np.nan
            continue

        try:
            durations = _analyze_lead_pwave(signal, fs)
            lead_means[lead] = float(np.mean(durations)) if durations else np.nan
        except Exception as e:
            print(f"  [p_wave_module] Lead {lead} failed: {e}")
            lead_means[lead] = np.nan

    for lead, mean_val in lead_means.items():
        result[f"P_Duration_{lead}_ms"] = mean_val

    # P-Wave Dispersion (PWD) = max lead average - min lead average
    valid_values = [v for v in lead_means.values() if not np.isnan(v)]
    if len(valid_values) >= 2:
        result["P_Wave_Dispersion_ms"] = float(max(valid_values) - min(valid_values))
    else:
        result["P_Wave_Dispersion_ms"] = np.nan

    # Backwards-compatible single-lead summary (reference lead only)
    ref_signal = cleaned_leads.get(reference_lead)
    result["P_Duration_mean_ms"] = np.nan
    result["P_Duration_std_ms"] = np.nan
    result["P_Wave_Count"] = 0

    if ref_signal is not None:
        durations = _analyze_lead_pwave(ref_signal, fs)
        if durations:
            result["P_Duration_mean_ms"] = float(np.mean(durations))
            result["P_Duration_std_ms"] = float(np.std(durations))
            result["P_Wave_Count"] = len(durations)

    return result
