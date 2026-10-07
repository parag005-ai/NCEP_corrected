"""ECG Visualization Engine package (Sprint 4).

Converts the canonical waveform of a recording into report-ready graphics.
Phase 1 produces the raw ECG rhythm strip; the annotated visualizations of
Phase 2 (beat markers, P-wave, QRS, QT, SAECG, quality overlays) plug in as
additional renderers without changing this architecture.

The engine renders only. It performs no clinical interpretation, no beat
annotation, no parameter calculation and no signal processing.
"""

from app.reporting.visualizations.engine import (
    VISUALIZATION_TYPE_RAW_ECG,
    ECGVisualizationEngine,
    VisualizationResult,
)
from app.reporting.visualizations.rendering_policy import (
    DEFAULT_WINDOW_SECONDS,
    SVG_CONTENT_TYPE,
)
from app.reporting.visualizations.selection import (
    DEFAULT_LEAD,
    FALLBACK_LEADS,
    SignalValidation,
    VisualizationWindow,
    select_lead,
    select_window,
    validate_signal,
)
from app.reporting.visualizations.svg_renderer import RawECGSVGRenderer, RhythmStrip
from app.reporting.visualizations.waveform_reader import WaveformData, WaveformReader

__all__ = [
    "DEFAULT_LEAD",
    "DEFAULT_WINDOW_SECONDS",
    "ECGVisualizationEngine",
    "FALLBACK_LEADS",
    "RawECGSVGRenderer",
    "RhythmStrip",
    "SVG_CONTENT_TYPE",
    "SignalValidation",
    "VISUALIZATION_TYPE_RAW_ECG",
    "VisualizationResult",
    "VisualizationWindow",
    "WaveformData",
    "WaveformReader",
    "select_lead",
    "select_window",
    "validate_signal",
]
