"""
preprocessing.py
=================
SINGLE SHARED PREPROCESSING STEP for the whole team's pipeline.

This is run exactly ONCE per patient, per lead. The cleaned signal it
produces is then reused by p_wave_module.py, qrs_module.py, and
t_wave_module.py -- none of those modules should filter the signal again.

Filter chain (taken from task_bb.py, since it was the most complete):
  1. Bandpass filter (0.5-40 Hz)      -> removes noise outside ECG band
  2. Baseline wander removal           -> removes slow drift
  3. neurokit2 ecg_clean (method='neurokit') -> final polish/normalization
"""

import numpy as np
import wfdb
from scipy.signal import butter, filtfilt
import neurokit2 as nk


# ==========================================================
# LOAD A WFDB RECORD (patientXXX.hea / patientXXX.dat)
# ==========================================================

def load_wfdb_record(record_path):
    """
    record_path: path WITHOUT extension, e.g. 'data/patient001/patient001'

    Returns:
        signal_matrix : np.ndarray, shape (n_samples, n_leads)
        lead_names    : list[str], e.g. ['I','II','III','AVR','AVL','AVF',
                                          'V1','V2','V3','V4','V5','V6']
        fs            : int, sampling rate in Hz
    """
    record = wfdb.rdrecord(record_path)
    signal_matrix = record.p_signal
    lead_names = [name.strip().upper() for name in record.sig_name]
    fs = record.fs
    return signal_matrix, lead_names, fs


# ==========================================================
# FILTER CHAIN
# ==========================================================

def bandpass_filter(signal, lowcut=0.5, highcut=40, fs=1000, order=4):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, signal)


def remove_baseline(signal, fs):
    baseline = nk.signal_filter(
        signal,
        sampling_rate=fs,
        lowcut=None,
        highcut=0.5,
        method="butterworth",
        order=2
    )
    return signal - baseline


def preprocess_signal(signal, fs):
    """Runs the full filter chain on ONE lead. Called once per lead."""
    signal = np.asarray(signal, dtype=float)

    # Handle missing samples before filtering
    if np.isnan(signal).any():
        signal = np.nan_to_num(signal, nan=np.nanmedian(signal))

    signal = bandpass_filter(signal, lowcut=0.5, highcut=40, fs=fs, order=4)
    signal = remove_baseline(signal, fs)
    signal = nk.ecg_clean(signal, sampling_rate=fs, method="neurokit")

    return signal


def preprocess_record(signal_matrix, lead_names, fs):
    """
    Preprocesses every lead of a patient's record ONCE.

    Returns: dict {lead_name: cleaned_signal}
    """
    cleaned = {}
    for i, lead in enumerate(lead_names):
        raw = signal_matrix[:, i]
        try:
            cleaned[lead] = preprocess_signal(raw, fs)
        except Exception as e:
            print(f"  [preprocessing] Lead {lead} failed: {e}")
            cleaned[lead] = None
    return cleaned
