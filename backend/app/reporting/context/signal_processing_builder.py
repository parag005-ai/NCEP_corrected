"""Builds the Generation Context's Signal Processing sections from real data.

This is the integration seam ``generation_context.py`` documents: "When
Signal Processing is integrated, those sections gain a payload -- no
structural change to this model, the loader, the builders or the templates
is required." This module is that integration -- it does not change the
shape of ``SignalProcessingOutputs``, it only populates it.

Deliberately populates five of the six sections (raw measurements) and
leaves ``clinical_findings`` awaiting: classification/scoring and clinical
narrative require the medical team's confirmed thresholds and are not
authored here (see app/signal_processing/README.md).

Never raises: a waveform that cannot be read, or a bug in the analysis
adapter, degrades to the Phase 1 all-awaiting state rather than failing
report generation, since Signal Processing is additive to a report that
was already generatable without it.
"""

from __future__ import annotations

import logging

from app.reporting.constants import SectionStatus
from app.reporting.context.generation_context import ContextSection, SignalProcessingOutputs
from app.reporting.exceptions import WaveformReadError
from app.reporting.models.ecg_artifacts import ECGArtifactBundle
from app.reporting.visualizations.waveform_reader import WaveformReader
from app.signal_processing.analysis import SignalProcessingResult, analyze_waveform

logger = logging.getLogger(__name__)


def _to_uv(value_mv: float | None) -> float | None:
    """RMS20/RMS40 are computed in mV; the report displays them in µV."""
    return None if value_mv is None else value_mv * 1000.0


def _ecg_parameters(result: SignalProcessingResult) -> dict:
    lead = result.reference_lead
    get = result.get
    return {
        "reference_lead": lead,
        "heart_rate_bpm": get("Heart_Rate_bpm"),
        "qrs_duration_median_ms": get("QRS_Duration_median_ms"),
        "qrs_duration_mean_ms": get("QRS_Duration_mean_ms"),
        "rr_interval_ms": get(f"Avg_RR_{lead}_ms"),
        "qt_interval_ms": get(f"Avg_QT_{lead}_ms"),
        "qtc_bazett_ms": get(f"Avg_QTc_Bazett_{lead}_ms"),
        "qtc_fridericia_ms": get(f"Avg_QTc_Fridericia_{lead}_ms"),
        "tpe_ms": get(f"Avg_Tpe_{lead}_ms"),
        "tpe_qt_ratio_global": get("Avg_Tpe_Qt_ratio_GLOBAL"),
        "qt_dispersion_global_ms": get("QT_dispersion_global_ms"),
        "t_wave_dispersion_ms": get("T_Wave_Dispersion_ms"),
    }


def _clinical_measurements(result: SignalProcessingResult) -> dict:
    get = result.get
    return {
        "p_duration_ms": get("P_Duration_mean_ms"),
        "p_wave_dispersion_ms": get("P_Wave_Dispersion_ms"),
        "filtered_p_duration_ms": get("Filtered_P_Duration_ms"),
        "rms20_uv": _to_uv(get("RMS20_mV")),
        "las20_ms": get("LAS20_ms"),
        "filtered_qrs_duration_ms": get("Filtered_QRS_Duration_ms"),
        "rms40_uv": _to_uv(get("QRS_RMS40_mV")),
        "las40_ms": get("QRS_LAS40_ms"),
    }


def _signal_quality_metrics(result: SignalProcessingResult) -> dict:
    return {
        "preprocessing_status": result.preprocessing_status,
        "qrs_qc_status": result.get("QRS_QC_Status"),
        "qrs_delineation_method": result.get("QRS_Delineation_Method"),
        "r_peak_count": result.r_peak_count,
        "leads_analyzed": list(result.leads_analyzed),
    }


def _beat_selection(result: SignalProcessingResult) -> dict:
    get = result.get
    return {
        "qrs_saecg_beats_extracted": get("QRS_SAECG_Beats_Extracted"),
        "qrs_saecg_beats_used": get("QRS_SAECG_Beats_Used"),
        "qrs_saecg_beats_rejected": get("QRS_SAECG_Beats_Rejected"),
        "qrs_saecg_snr_db": get("QRS_SAECG_SNR_dB"),
        "p_saecg_beats_used": get("P_SAECG_Beats_Used"),
        "p_saecg_snr_db": get("P_SAECG_SNR_dB"),
    }


def build_signal_processing_outputs(
    artifacts: ECGArtifactBundle,
    *,
    ecg_record_id: str,
    fallback_sampling_rate_hz: float | None,
    fallback_units: str | None,
) -> SignalProcessingOutputs:
    """Runs the vendored ECG pipeline and maps its output onto the context.

    Falls back to the Phase 1 all-awaiting state (never raises) if the
    waveform cannot be read or the analysis adapter fails unexpectedly --
    the report is still generatable, just without Signal Processing data,
    exactly as it was before this integration existed.
    """
    try:
        waveform = WaveformReader().read_from_artifacts(
            artifacts,
            ecg_record_id=ecg_record_id,
            fallback_sampling_rate_hz=fallback_sampling_rate_hz,
            fallback_units=fallback_units,
        )
        result = analyze_waveform(dict(waveform.leads), waveform.sampling_rate_hz)
    except WaveformReadError as exc:
        logger.warning("signal_processing: waveform unreadable for %s: %s", ecg_record_id, exc)
        return SignalProcessingOutputs.awaiting_signal_processing()
    except Exception:  # noqa: BLE001 -- a bug here must degrade, not break report generation
        logger.exception("signal_processing: analysis failed unexpectedly for %s", ecg_record_id)
        return SignalProcessingOutputs.awaiting_signal_processing()

    return SignalProcessingOutputs(
        ecg_parameters=ContextSection(
            name="ECG Parameters", status=SectionStatus.AVAILABLE, payload=_ecg_parameters(result)
        ),
        clinical_measurements=ContextSection(
            name="Clinical Measurements", status=SectionStatus.AVAILABLE, payload=_clinical_measurements(result)
        ),
        signal_quality_metrics=ContextSection(
            name="Signal Quality Metrics", status=SectionStatus.AVAILABLE, payload=_signal_quality_metrics(result)
        ),
        # No plotting/annotation value is exposed by the authoritative result.
        waveform_annotations=ContextSection.unavailable(
            "Waveform Annotations",
            "Waveform annotation is not produced by Signal Processing",
        ),
        beat_selection=ContextSection(
            name="Beat Selection Information", status=SectionStatus.AVAILABLE, payload=_beat_selection(result)
        ),
        # Classification/scoring and narrative interpretation require the
        # medical team's confirmed thresholds -- not authored here.
        clinical_findings=ContextSection.unavailable(
            "Clinical Findings",
            "Clinical result unavailable: approved decision limits are not configured",
        ),
    )
