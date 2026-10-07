"""Adapter between plain lead-sample arrays and the biomedical team's ECG modules.

Mirrors ``pipeline.py``'s per-patient logic (same call order, same
reference-lead selection and fallback) from the vendored pipeline, but reads
already-loaded lead arrays instead of a WFDB file from disk, and normalizes
NCEP's lead names to the upper-case form these modules expect (NCEP:
``aVR``/``aVL``/``aVF``; these modules: ``AVR``/``AVL``/``AVF``).

Deliberately takes plain ``dict[str, np.ndarray]`` + sampling rate rather
than NCEP's own ``WaveformData`` type: this package is the vendored
biomedical pipeline and must not depend on the reporting subsystem's
internal types (doing so previously created a circular import, since
reporting's context loader depends on this package). The reporting side
(``app/reporting/context/signal_processing_builder.py``) does that
conversion.

Contains no clinical logic of its own: only format conversion and
orchestration. See README.md in this package for what is deliberately
excluded from this integration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.signal_processing.p_saecg_module import analyze_p_saecg
from app.signal_processing.p_wave_module import analyze_pwave
from app.signal_processing.preprocessing import preprocess_signal
from app.signal_processing.qrs_module import analyze_qrs
from app.signal_processing.qrs_saecg_module import analyze_qrs_saecg
from app.signal_processing.qt_module import analyze_qt
from app.signal_processing.t_wave_module import analyze_twave

logger = logging.getLogger(__name__)

#: Matches pipeline.py's REFERENCE_LEAD default -- lead II is the standard
#: choice for single-lead rhythm/QRS/SAECG analysis.
DEFAULT_REFERENCE_LEAD = "II"


@dataclass(frozen=True)
class SignalProcessingResult:
    """Every metric the vendored pipeline computed for one recording.

    ``metrics`` mirrors one row of the biomedical team's
    ``ECG_All_Patients_Results.csv`` (see their README for the full column
    reference) -- a flat dict of patient-level parameters, NaN where a
    metric could not be computed for this recording rather than fabricated.
    """

    reference_lead: str
    preprocessing_status: str
    leads_analyzed: tuple[str, ...]
    r_peak_count: int
    metrics: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str) -> float | int | str | None:
        """One metric, or None where the pipeline returned NaN/missing."""
        value = self.metrics.get(key)
        if value is None:
            return None
        if isinstance(value, float) and np.isnan(value):
            return None
        return value


def _normalize_leads(leads: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """NCEP stores mixed-case lead names (aVR/aVL/aVF); these modules expect upper-case."""
    return {name.upper(): samples for name, samples in leads.items()}


def _preprocess_leads(leads: dict[str, np.ndarray], fs: float) -> dict[str, np.ndarray | None]:
    """Same per-lead filter chain and failure handling as preprocessing.py's preprocess_record,
    applied directly to already-loaded lead arrays instead of a signal matrix."""
    cleaned: dict[str, np.ndarray | None] = {}
    for lead, raw in leads.items():
        try:
            cleaned[lead] = preprocess_signal(raw, fs)
        except Exception as exc:  # noqa: BLE001 -- one lead's failure must not abort the recording
            logger.warning("signal_processing: lead %s failed preprocessing: %s", lead, exc)
            cleaned[lead] = None
    return cleaned


def analyze_waveform(
    leads: dict[str, np.ndarray], sampling_rate_hz: float, *, reference_lead: str = DEFAULT_REFERENCE_LEAD
) -> SignalProcessingResult:
    """Runs the full vendored pipeline against one recording's leads.

    Never raises for a signal-processing failure: a lead, or an entire
    analysis module, that cannot produce a result contributes NaN/empty
    fields (exactly as the vendored modules already do for a single patient
    in a multi-patient batch run) rather than aborting report generation.
    Only called with already-verified-readable lead samples, so this
    function's own failure modes are unexpected bugs, not missing data.
    """
    raw_leads = _normalize_leads(dict(leads))
    fs = sampling_rate_hz

    cleaned_leads = _preprocess_leads(raw_leads, fs)
    leads_ok = sum(1 for v in cleaned_leads.values() if v is not None)
    if leads_ok == 0:
        preprocessing_status = "failed"
    elif leads_ok < len(cleaned_leads):
        preprocessing_status = "partial"
    else:
        preprocessing_status = "success"

    ref_lead = reference_lead.upper()
    if ref_lead not in cleaned_leads or cleaned_leads[ref_lead] is None:
        # Matches pipeline.py's fallback: first available (successfully
        # preprocessed) lead, so a recording missing lead II still analyzes.
        ref_lead = next((lead for lead, signal in cleaned_leads.items() if signal is not None), ref_lead)
    ref_signal = cleaned_leads.get(ref_lead)

    metrics: dict[str, Any] = {}
    r_peaks: np.ndarray = np.array([], dtype=int)

    if ref_signal is not None:
        try:
            metrics.update(analyze_pwave(cleaned_leads, ref_lead, fs))
        except Exception as exc:  # noqa: BLE001
            logger.warning("signal_processing: P-wave analysis failed: %s", exc)

        try:
            qrs_result, r_peaks = analyze_qrs(ref_signal, fs)
            metrics.update(qrs_result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("signal_processing: QRS analysis failed: %s", exc)

        try:
            metrics.update(analyze_twave(cleaned_leads, r_peaks, fs))
        except Exception as exc:  # noqa: BLE001
            logger.warning("signal_processing: T-wave analysis failed: %s", exc)

        try:
            metrics.update(analyze_qt(cleaned_leads, fs))
        except Exception as exc:  # noqa: BLE001
            logger.warning("signal_processing: QT/QTc analysis failed: %s", exc)

        try:
            metrics.update(analyze_p_saecg(ref_signal, r_peaks, fs))
        except Exception as exc:  # noqa: BLE001
            logger.warning("signal_processing: P-SAECG analysis failed: %s", exc)

        try:
            metrics.update(analyze_qrs_saecg(ref_signal, r_peaks, fs))
        except Exception as exc:  # noqa: BLE001
            logger.warning("signal_processing: QRS-SAECG analysis failed: %s", exc)
    else:
        logger.warning("signal_processing: no lead preprocessed successfully; no metrics computed")

    return SignalProcessingResult(
        reference_lead=ref_lead,
        preprocessing_status=preprocessing_status,
        leads_analyzed=tuple(lead for lead, signal in cleaned_leads.items() if signal is not None),
        r_peak_count=int(len(r_peaks)),
        metrics=metrics,
    )
