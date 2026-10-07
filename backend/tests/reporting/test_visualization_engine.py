"""Tests for the ECG Visualization Engine (Sprint 4)."""

from __future__ import annotations

import io

import numpy as np
import pytest

from app.reporting.constants import ArtifactType
from app.reporting.context import GenerationContextLoader
from app.reporting.exceptions import SVGRenderingError, WaveformReadError
from app.reporting.repositories import ECGArtifactRepository
from app.reporting.repositories.job_repository import ReportGenerationJobRepository
from app.reporting.storage import ReportArtifactStore
from app.reporting.visualizations import (
    DEFAULT_LEAD,
    ECGVisualizationEngine,
    RawECGSVGRenderer,
    RhythmStrip,
    WaveformReader,
    select_lead,
    select_window,
    validate_signal,
)

from tests.reporting.conftest import write_canonical_artifacts

SAMPLING_RATE_HZ = 1000.0


# ---------------------------------------------------------------------------
# Signal validation (Sprint 4.6)
# ---------------------------------------------------------------------------


def test_a_normal_recording_is_usable():
    assert validate_signal(SAMPLING_RATE_HZ, {"II": np.ones(100)}).is_usable


@pytest.mark.parametrize(
    ("sampling_rate_hz", "leads", "expected"),
    [
        (SAMPLING_RATE_HZ, {}, "no leads"),
        (0.0, {"II": np.ones(10)}, "unusable sampling rate"),
        (float("nan"), {"II": np.ones(10)}, "unusable sampling rate"),
        (SAMPLING_RATE_HZ, {"II": np.array([])}, "no samples"),
        (SAMPLING_RATE_HZ, {"II": np.array([1.0, np.nan])}, "numerically valid"),
    ],
)
def test_an_undrawable_recording_is_reported_with_a_reason(sampling_rate_hz, leads, expected):
    validation = validate_signal(sampling_rate_hz, leads)

    assert not validation.is_usable
    assert expected in validation.reason


# ---------------------------------------------------------------------------
# Lead selection (Sprint 4.7)
# ---------------------------------------------------------------------------


def test_lead_two_is_the_default_rhythm_lead():
    leads = {name: np.ones(10) for name in ("I", "II", "V1", "V5")}

    assert select_lead(leads) == DEFAULT_LEAD


@pytest.mark.parametrize(
    ("available", "expected"),
    [
        (("I", "V1", "V5"), "I"),
        (("V1", "V5"), "V5"),
        (("V1", "V3"), "V1"),
        (("V3", "aVR"), "aVR"),
    ],
)
def test_lead_selection_follows_the_declared_fallback_order(available, expected):
    leads = {name: np.ones(10) for name in available}

    assert select_lead(leads) == expected


def test_a_present_but_unusable_lead_is_skipped():
    leads = {"II": np.array([np.nan, np.nan]), "I": np.ones(10)}

    assert select_lead(leads) == "I"


def test_no_usable_lead_yields_no_selection():
    assert select_lead({"II": np.array([np.inf])}) is None
    assert select_lead({}) is None


# ---------------------------------------------------------------------------
# Window selection (Sprint 4.8)
# ---------------------------------------------------------------------------


def test_a_long_recording_is_shown_as_a_representative_strip():
    window = select_window(60_000, SAMPLING_RATE_HZ, window_seconds=10.0)

    assert (window.start_second, window.end_second) == (0.0, 10.0)
    assert (window.start_index, window.end_index) == (0, 10_000)


def test_a_short_recording_is_shown_whole():
    window = select_window(2_500, SAMPLING_RATE_HZ, window_seconds=10.0)

    assert window.duration_seconds == 2.5
    assert window.end_index == 2_500


# ---------------------------------------------------------------------------
# SVG rendering (Sprint 4.9 - 4.11 / 4.14)
# ---------------------------------------------------------------------------


def build_strip(samples: np.ndarray | None = None, lead: str = "II") -> RhythmStrip:
    if samples is None:
        t = np.arange(1000) / SAMPLING_RATE_HZ
        samples = np.sin(2 * np.pi * 1.2 * t)
    return RhythmStrip(lead=lead, samples=samples, sampling_rate_hz=SAMPLING_RATE_HZ, start_second=0.0)


def test_the_strip_carries_a_grid_baseline_calibration_and_trace():
    svg = RawECGSVGRenderer().render(build_strip()).decode("utf-8")

    assert svg.startswith('<?xml version="1.0" encoding="UTF-8"?><svg')
    assert svg.rstrip().endswith("</svg>")
    for part in ("ecg-grid", "ecg-baseline", "ecg-calibration", "ecg-trace"):
        assert f'class="{part}"' in svg
    assert "25 mm/s" in svg and "10 mm/mV" in svg
    assert "Lead II" in svg


def test_rendering_is_deterministic():
    """Identical input must produce byte-identical output (Sprint 4.14)."""
    strip = build_strip()

    assert RawECGSVGRenderer().render(strip) == RawECGSVGRenderer().render(strip)


def test_the_strip_is_drawn_at_standard_scale():
    """One second occupies 25 mm; the strip is 40 mm tall."""
    renderer = RawECGSVGRenderer(pixels_per_mm=4.0)

    svg = renderer.render(build_strip()).decode("utf-8")

    # 10 mm calibration gutter + 1 s at 25 mm/s = 35 mm at 4 px/mm.
    assert 'width="140"' in svg
    assert 'height="160"' in svg


def test_a_long_recording_is_decimated_for_display_only():
    renderer = RawECGSVGRenderer(max_render_points=500)
    dense = build_strip(samples=np.zeros(50_000))

    svg = renderer.render(dense).decode("utf-8")
    drawn_points = svg.count("L", svg.index('class="ecg-trace"'))

    assert drawn_points <= 500


def test_an_empty_or_invalid_strip_cannot_be_rendered():
    with pytest.raises(SVGRenderingError, match="no samples"):
        RawECGSVGRenderer().render(build_strip(samples=np.array([])))
    with pytest.raises(SVGRenderingError, match="non-numeric"):
        RawECGSVGRenderer().render(build_strip(samples=np.array([1.0, np.nan])))


# ---------------------------------------------------------------------------
# Waveform reading (Sprint 4.5)
# ---------------------------------------------------------------------------


@pytest.fixture
def context(session, upstream, artifact_store):
    """A Generation Context for a fully ingested recording."""

    def _build(**write_kwargs):
        write_canonical_artifacts(artifact_store, upstream.canonical_record_id, **write_kwargs)
        job = ReportGenerationJobRepository(session).create(
            ecg_record_id=upstream.ecg_record_id,
            patient_id=upstream.patient_id,
            organisation_id=upstream.organisation_id,
            requested_by_user_id=upstream.user_id,
        )
        loader = GenerationContextLoader(session, artifacts=ECGArtifactRepository(store=artifact_store))
        return loader.load(job), job

    return _build


def test_the_reader_returns_every_stored_lead(context):
    generation_context, _ = context()

    waveform = WaveformReader().read(generation_context)

    assert set(waveform.available_leads) == {"I", "II", "V1"}
    assert waveform.sampling_rate_hz == SAMPLING_RATE_HZ
    assert waveform.leads["II"].size == 10_000


def test_a_corrupt_waveform_artifact_is_a_critical_failure(context):
    generation_context, _ = context(waveform_bytes=b"not an npz archive")

    with pytest.raises(WaveformReadError, match="could not be read"):
        WaveformReader().read(generation_context)


def test_unconvertible_units_are_refused_rather_than_guessed(context):
    """Drawing at an unknown gain would misrepresent amplitudes (Sprint 4.14)."""
    generation_context, _ = context(units="furlongs")

    with pytest.raises(WaveformReadError, match="millivolts"):
        WaveformReader().read(generation_context)


def test_microvolt_recordings_are_normalised_to_millivolts(context):
    """Unit normalization keeps every strip at a comparable gain (Sprint 2.4.4)."""
    buffer = io.BytesIO()
    np.savez_compressed(buffer, II=np.full(1000, 1500.0))  # 1500 uV == 1.5 mV
    generation_context, _ = context(waveform_bytes=buffer.getvalue(), units="uV")

    waveform = WaveformReader().read(generation_context)

    assert waveform.source_units == "uV"
    assert waveform.leads["II"][0] == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# The engine end to end (Sprint 4.3 / 4.12)
# ---------------------------------------------------------------------------


def test_the_engine_stores_a_strip_and_describes_it(context, tmp_path):
    generation_context, job = context()
    store = ReportArtifactStore(root=tmp_path / "reports")

    result = ECGVisualizationEngine(store).generate_raw_ecg(generation_context, job_id=job.id)

    assert result.is_available
    artifact = result.artifact
    assert artifact.artifact_type is ArtifactType.RAW_ECG_SVG
    assert artifact.content_type == "image/svg+xml"
    assert artifact.storage_location == "visualizations/raw_ecg_lead_II.svg"
    assert artifact.file_size_bytes > 0
    assert len(artifact.checksum_sha256) == 64
    assert artifact.artifact_metadata["lead"] == "II"
    assert artifact.artifact_metadata["visualization_type"] == "RAW_ECG"
    assert artifact.artifact_metadata["window_start_second"] == 0.0
    assert artifact.artifact_metadata["window_end_second"] == 10.0
    assert artifact.artifact_metadata["ecg_record_id"] == generation_context.ecg.ecg_record_id


def test_the_stored_file_matches_its_recorded_checksum(context, tmp_path):
    import hashlib
    from pathlib import Path

    generation_context, job = context()
    store = ReportArtifactStore(root=tmp_path / "reports")

    artifact = ECGVisualizationEngine(store).generate_raw_ecg(
        generation_context, job_id=job.id
    ).artifact
    written = Path(artifact.absolute_path).read_bytes()

    assert hashlib.sha256(written).hexdigest() == artifact.checksum_sha256
    assert len(written) == artifact.file_size_bytes
    assert written.startswith(b'<?xml version="1.0"')


def test_artifacts_are_stored_under_the_generating_job(context, tmp_path):
    generation_context, job = context()
    store = ReportArtifactStore(root=tmp_path / "reports")

    artifact = ECGVisualizationEngine(store).generate_raw_ecg(
        generation_context, job_id=job.id
    ).artifact

    assert str(store.job_dir(generation_context.ecg.ecg_record_id, job.id)) in artifact.absolute_path


def test_an_undrawable_recording_yields_no_artifact_and_a_reason(context, tmp_path):
    buffer = io.BytesIO()
    np.savez_compressed(buffer, II=np.array([np.nan, np.nan]))
    generation_context, job = context(waveform_bytes=buffer.getvalue())
    store = ReportArtifactStore(root=tmp_path / "reports")

    result = ECGVisualizationEngine(store).generate_raw_ecg(generation_context, job_id=job.id)

    assert not result.is_available
    assert result.artifact is None
    assert result.unavailable_reason
    assert not (tmp_path / "reports").exists()


def test_generation_is_reproducible_for_the_same_recording(context, tmp_path):
    """Regenerating a report must produce the same image (Sprint 4.14)."""
    from pathlib import Path

    generation_context, job = context()
    engine = ECGVisualizationEngine(ReportArtifactStore(root=tmp_path / "reports"))

    first = engine.generate_raw_ecg(generation_context, job_id=job.id).artifact
    second = engine.generate_raw_ecg(generation_context, job_id="rgj-other").artifact

    assert first.checksum_sha256 == second.checksum_sha256
    assert Path(first.absolute_path).read_bytes() == Path(second.absolute_path).read_bytes()
