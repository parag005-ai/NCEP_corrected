from __future__ import annotations

import numpy as np
import pytest

from app.ecg.constants import CanonicalLead
from app.ecg.models.waveform import LeadSignal, Waveform
from app.preprocessing.baseline_correction import remove_baseline_wander
from app.preprocessing.beat_detection import detect_beats
from app.preprocessing.filtering import apply_filters
from app.preprocessing.normalization import z_score_normalize
from app.preprocessing.pipeline import (
    PreprocessingOrchestrator,
    generate_preprocessed_artifact,
    generate_preprocessing_report,
)
from app.preprocessing.signal_quality import assess_quality

SAMPLING_RATE_HZ = 250.0


def _simulated_ecg(duration_s: int = 10, heart_rate: int = 72, noise: float = 0.02) -> np.ndarray:
    neurokit2 = pytest.importorskip("neurokit2")
    return np.asarray(
        neurokit2.ecg_simulate(
            duration=duration_s,
            sampling_rate=int(SAMPLING_RATE_HZ),
            heart_rate=heart_rate,
            noise=noise,
            random_state=42,
        ),
        dtype=np.float64,
    )


def _waveform(samples: np.ndarray, lead: CanonicalLead = CanonicalLead.II) -> Waveform:
    return Waveform(leads={lead: LeadSignal(lead, samples)}, sampling_rate_hz=SAMPLING_RATE_HZ, units="mV")


def test_bandpass_and_notch_preserve_length_and_reduce_high_frequency_noise():
    rng = np.random.default_rng(0)
    t = np.arange(0, 4, 1 / SAMPLING_RATE_HZ)
    clean = np.sin(2 * np.pi * 5 * t)
    noisy = clean + 0.5 * np.sin(2 * np.pi * 100 * t) + 0.1 * rng.standard_normal(t.shape)

    filtered = apply_filters(noisy, SAMPLING_RATE_HZ)

    assert filtered.shape == noisy.shape
    # The 100 Hz interference sits outside the 0.5-40 Hz passband and should be attenuated.
    assert np.std(filtered - clean) < np.std(noisy - clean)


def test_apply_filters_does_not_raise_on_very_short_signal():
    short = np.array([0.1, 0.2, 0.3, -0.1])
    filtered = apply_filters(short, SAMPLING_RATE_HZ)
    assert filtered.shape == short.shape


def test_remove_baseline_wander_flattens_slow_drift():
    t = np.arange(0, 10, 1 / SAMPLING_RATE_HZ)
    drift = 2.0 * np.sin(2 * np.pi * 0.05 * t)
    signal = drift + 0.05 * np.sin(2 * np.pi * 10 * t)

    corrected = remove_baseline_wander(signal, SAMPLING_RATE_HZ)

    assert corrected.shape == signal.shape
    assert np.std(corrected) < np.std(signal)


def test_z_score_normalize_produces_zero_mean_unit_variance():
    samples = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    normalized = z_score_normalize(samples)
    assert np.isclose(np.mean(normalized), 0.0)
    assert np.isclose(np.std(normalized), 1.0)


def test_z_score_normalize_handles_flat_signal_without_dividing_by_zero():
    samples = np.full(100, 3.0)
    normalized = z_score_normalize(samples)
    assert np.all(np.isfinite(normalized))
    assert np.allclose(normalized, 0.0)


def test_detect_beats_on_simulated_ecg_matches_expected_heart_rate():
    ecg = _simulated_ecg(duration_s=10, heart_rate=72, noise=0.0)
    result = detect_beats(ecg, SAMPLING_RATE_HZ)
    assert result.beat_count >= 9  # ~12 expected in 10s at 72bpm, allow edge-effect slack
    assert result.mean_heart_rate_bpm is not None
    assert 60.0 <= result.mean_heart_rate_bpm <= 85.0


def test_detect_beats_returns_empty_result_for_too_short_signal():
    result = detect_beats(np.zeros(10), SAMPLING_RATE_HZ)
    assert result == type(result)((), 0, None)


def test_assess_quality_flags_flatline_and_scores_zero():
    flat = np.zeros(2500)
    result = assess_quality(flat, flat, beat_count=0, duration_seconds=10.0)
    assert "flatline" in result.flags
    assert result.quality_score == 0.0


def test_assess_quality_flags_clipping():
    raw = np.concatenate([np.full(50, 5.0), np.random.default_rng(0).normal(0, 0.1, 200), np.full(50, 5.0)])
    result = assess_quality(raw, raw, beat_count=5, duration_seconds=1.0)
    assert "clipping" in result.flags


def test_assess_quality_clean_signal_has_no_flags_and_positive_score():
    ecg = _simulated_ecg(duration_s=10, heart_rate=72, noise=0.02)
    filtered = remove_baseline_wander(apply_filters(ecg, SAMPLING_RATE_HZ), SAMPLING_RATE_HZ)
    beats = detect_beats(filtered, SAMPLING_RATE_HZ)
    result = assess_quality(ecg, filtered, beats.beat_count, duration_seconds=10.0)
    assert result.flags == ()
    assert result.quality_score > 0.0


def test_pipeline_end_to_end_on_simulated_ecg():
    ecg = _simulated_ecg(duration_s=10, heart_rate=72, noise=0.02)
    waveform = _waveform(ecg)

    result = PreprocessingOrchestrator.run(waveform)

    assert set(result.leads) == {CanonicalLead.II}
    assert result.beat_count >= 9
    assert 0.0 < result.quality_score <= 1.0
    assert result.quality_flags == ()

    lead_result = result.leads[CanonicalLead.II]
    assert lead_result.filtered_samples.shape == ecg.shape
    assert lead_result.beats.mean_heart_rate_bpm is not None


def test_pipeline_handles_degenerate_flatline_lead():
    waveform = _waveform(np.zeros(2500), lead=CanonicalLead.I)
    result = PreprocessingOrchestrator.run(waveform)
    assert result.beat_count == 0
    assert result.quality_score == 0.0
    assert "flatline" in result.quality_flags


def test_generate_preprocessed_artifact_round_trips_through_npz():
    import io

    ecg = _simulated_ecg(duration_s=5, heart_rate=70)
    waveform = _waveform(ecg)
    result = PreprocessingOrchestrator.run(waveform)

    npz_bytes = generate_preprocessed_artifact(result)
    with np.load(io.BytesIO(npz_bytes)) as npz:
        assert "II" in npz.files
        assert npz["II"].shape == ecg.shape


def test_generate_preprocessing_report_is_json_serializable():
    import json

    ecg = _simulated_ecg(duration_s=5, heart_rate=70)
    waveform = _waveform(ecg)
    result = PreprocessingOrchestrator.run(waveform)

    report = generate_preprocessing_report(result)
    serialized = json.dumps(report)  # must not raise

    assert "beat_count" in report
    assert "II" in report["leads"]
    assert json.loads(serialized)["leads"]["II"]["beat_count"] == report["leads"]["II"]["beat_count"]
