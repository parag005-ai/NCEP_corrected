"""Exact, calculation-free mapping from authoritative SP output to report context."""

from types import SimpleNamespace

import numpy as np

from app.reporting.constants import SectionStatus
from app.reporting.context import signal_processing_builder as mapping
from app.signal_processing.analysis import SignalProcessingResult


def test_every_supported_sp_field_is_copied_to_generation_context(monkeypatch):
    result = SignalProcessingResult(
        reference_lead="II",
        preprocessing_status="success",
        leads_analyzed=("I", "II", "V1"),
        r_peak_count=139,
        metrics={
            "Heart_Rate_bpm": 72,
            "QRS_Duration_median_ms": 82,
            "QRS_Duration_mean_ms": 83.25,
            "Avg_RR_II_ms": 830.0,
            "Avg_QT_II_ms": 401,
            "Avg_QTc_Bazett_II_ms": 440,
            "Avg_QTc_Fridericia_II_ms": 426,
            "Avg_Tpe_II_ms": 77,
            "Avg_Tpe_Qt_ratio_GLOBAL": 0.192,
            "QT_dispersion_global_ms": 198,
            "T_Wave_Dispersion_ms": 52,
            "P_Duration_mean_ms": 86,
            "P_Wave_Dispersion_ms": 44,
            "Filtered_P_Duration_ms": 39,
            "RMS20_mV": 0.0042,
            "LAS20_ms": 3,
            "Filtered_QRS_Duration_ms": 97,
            "QRS_RMS40_mV": 0.0195,
            "QRS_LAS40_ms": 27,
            "QRS_QC_Status": "PASS",
            "QRS_Delineation_Method": "prominence",
            "QRS_SAECG_Beats_Extracted": 139,
            "QRS_SAECG_Beats_Used": 132,
            "QRS_SAECG_Beats_Rejected": 7,
            "QRS_SAECG_SNR_dB": 18.75,
            "P_SAECG_Beats_Used": 125,
            "P_SAECG_SNR_dB": 16.5,
        },
    )
    monkeypatch.setattr(
        mapping.WaveformReader,
        "read_from_artifacts",
        lambda self, artifacts, **kwargs: SimpleNamespace(
            leads={"II": np.zeros(8)}, sampling_rate_hz=1000.0
        ),
    )
    monkeypatch.setattr(mapping, "analyze_waveform", lambda leads, sampling_rate_hz: result)

    outputs = mapping.build_signal_processing_outputs(
        object(),
        ecg_record_id="ecg-test",
        fallback_sampling_rate_hz=1000.0,
        fallback_units="mV",
    )

    assert dict(outputs.ecg_parameters.payload) == {
        "reference_lead": "II",
        "heart_rate_bpm": 72,
        "qrs_duration_median_ms": 82,
        "qrs_duration_mean_ms": 83.25,
        "rr_interval_ms": 830.0,
        "qt_interval_ms": 401,
        "qtc_bazett_ms": 440,
        "qtc_fridericia_ms": 426,
        "tpe_ms": 77,
        "tpe_qt_ratio_global": 0.192,
        "qt_dispersion_global_ms": 198,
        "t_wave_dispersion_ms": 52,
    }
    assert dict(outputs.clinical_measurements.payload) == {
        "p_duration_ms": 86,
        "p_wave_dispersion_ms": 44,
        "filtered_p_duration_ms": 39,
        "rms20_uv": 4.2,
        "las20_ms": 3,
        "filtered_qrs_duration_ms": 97,
        "rms40_uv": 19.5,
        "las40_ms": 27,
    }
    assert dict(outputs.signal_quality_metrics.payload) == {
        "preprocessing_status": "success",
        "qrs_qc_status": "PASS",
        "qrs_delineation_method": "prominence",
        "r_peak_count": 139,
        "leads_analyzed": ("I", "II", "V1"),
    }
    assert dict(outputs.beat_selection.payload) == {
        "qrs_saecg_beats_extracted": 139,
        "qrs_saecg_beats_used": 132,
        "qrs_saecg_beats_rejected": 7,
        "qrs_saecg_snr_db": 18.75,
        "p_saecg_beats_used": 125,
        "p_saecg_snr_db": 16.5,
    }

    assert not outputs.waveform_annotations.is_available
    assert not outputs.clinical_findings.is_available
    assert outputs.waveform_annotations.status is SectionStatus.NOT_AVAILABLE
    assert outputs.clinical_findings.status is SectionStatus.NOT_AVAILABLE

