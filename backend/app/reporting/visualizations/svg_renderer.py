"""Raw ECG SVG renderer (Sprint 4.9 - 4.11 / 4.14).

Draws one lead as a clinical rhythm strip: standard ECG grid, calibration
marker, baseline reference and the trace itself, at the conventional paper
speed and gain so a strip printed from any report is directly comparable to
any other (Sprint 4.14 Consistency).

    25 mm/s horizontally, 10 mm/mV vertically
    minor grid 1 mm = 40 ms / 0.1 mV, major grid 5 mm = 200 ms / 0.5 mV

Rendering is deterministic (Sprint 4.14): identical input produces
byte-identical output. Nothing time-varying, random or environment-dependent
is written into the document -- generation metadata belongs to the artifact
registry, not to the image.

The renderer performs no clinical interpretation and never alters stored
waveform data (Sprint 4.11). Sample decimation below is presentation-only: it
reduces the number of drawn points on a strip whose pixel resolution cannot
show them all, and leaves the stored recording untouched.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.reporting.exceptions import SVGRenderingError
from app.reporting.visualizations.rendering_policy import (
    BACKGROUND_COLOUR,
    CALIBRATION_AMPLITUDE_MV,
    CALIBRATION_COLOUR,
    CALIBRATION_DURATION_SECONDS,
    CALIBRATION_WIDTH_MM,
    LABEL_COLOUR,
    MAJOR_GRID_COLOUR,
    MAJOR_GRID_MM,
    MAX_RENDER_POINTS,
    MINOR_GRID_COLOUR,
    MINOR_GRID_MM,
    MM_PER_MILLIVOLT,
    MM_PER_SECOND,
    PIXELS_PER_MM,
    STRIP_HEIGHT_MM,
    TRACE_COLOUR,
)


@dataclass(frozen=True)
class RhythmStrip:
    """The signal and labels one rendered strip presents."""

    lead: str
    samples: np.ndarray
    sampling_rate_hz: float
    start_second: float


def _format(value: float) -> str:
    """Fixed-precision coordinate so output is byte-stable across platforms."""
    return f"{value:.2f}".rstrip("0").rstrip(".") if value % 1 else f"{int(value)}"


def _grid_path(width_px: float, height_px: float, spacing_px: float) -> str:
    segments = []
    steps = int(round(width_px / spacing_px))
    for step in range(steps + 1):
        x = step * spacing_px
        segments.append(f"M{_format(x)} 0V{_format(height_px)}")
    steps = int(round(height_px / spacing_px))
    for step in range(steps + 1):
        y = step * spacing_px
        segments.append(f"M0 {_format(y)}H{_format(width_px)}")
    return "".join(segments)


class RawECGSVGRenderer:
    """Renders one lead as a standard-scale ECG rhythm strip."""

    def __init__(
        self,
        *,
        pixels_per_mm: float = PIXELS_PER_MM,
        strip_height_mm: float = STRIP_HEIGHT_MM,
        max_render_points: int = MAX_RENDER_POINTS,
    ) -> None:
        self._pixels_per_mm = pixels_per_mm
        self._strip_height_mm = strip_height_mm
        self._max_render_points = max_render_points

    def render(self, strip: RhythmStrip) -> bytes:
        """Produces the complete SVG document for one rhythm strip.

        Raises:
            SVGRenderingError: the strip carries nothing drawable.
        """
        if strip.samples.size == 0:
            raise SVGRenderingError(f"Lead {strip.lead} has no samples to render")
        if not np.isfinite(strip.samples).all():
            raise SVGRenderingError(f"Lead {strip.lead} contains non-numeric samples")

        samples = self._decimate(strip.samples)
        duration_seconds = strip.samples.size / strip.sampling_rate_hz

        trace_width_px = duration_seconds * MM_PER_SECOND * self._pixels_per_mm
        calibration_width_px = CALIBRATION_WIDTH_MM * self._pixels_per_mm
        width_px = calibration_width_px + trace_width_px
        height_px = self._strip_height_mm * self._pixels_per_mm
        baseline_px = height_px / 2

        body = "".join(
            (
                self._grid(width_px, height_px),
                self._baseline(width_px, baseline_px),
                self._calibration_pulse(calibration_width_px, baseline_px),
                self._trace(samples, calibration_width_px, trace_width_px, baseline_px),
                self._labels(strip, width_px, height_px),
            )
        )
        document = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_format(width_px)}" '
            f'height="{_format(height_px)}" viewBox="0 0 {_format(width_px)} {_format(height_px)}" '
            f'role="img" aria-label="Raw ECG rhythm strip, lead {strip.lead}">'
            f"{body}</svg>"
        )
        return document.encode("utf-8")

    # ------------------------------------------------------------------
    # Document parts
    # ------------------------------------------------------------------

    def _grid(self, width_px: float, height_px: float) -> str:
        """The standard ECG grid, generated during rendering (Sprint 4.9)."""
        minor = _grid_path(width_px, height_px, MINOR_GRID_MM * self._pixels_per_mm)
        major = _grid_path(width_px, height_px, MAJOR_GRID_MM * self._pixels_per_mm)
        return (
            '<g class="ecg-grid">'
            f'<rect width="{_format(width_px)}" height="{_format(height_px)}" fill="{BACKGROUND_COLOUR}"/>'
            f'<path d="{minor}" stroke="{MINOR_GRID_COLOUR}" stroke-width="0.5" fill="none"/>'
            f'<path d="{major}" stroke="{MAJOR_GRID_COLOUR}" stroke-width="1" fill="none"/>'
            "</g>"
        )

    @staticmethod
    def _baseline(width_px: float, baseline_px: float) -> str:
        """The zero-amplitude reference the trace is drawn around (Sprint 4.9)."""
        return (
            f'<line class="ecg-baseline" x1="0" y1="{_format(baseline_px)}" '
            f'x2="{_format(width_px)}" y2="{_format(baseline_px)}" '
            f'stroke="{MAJOR_GRID_COLOUR}" stroke-width="0.75"/>'
        )

    def _calibration_pulse(self, calibration_width_px: float, baseline_px: float) -> str:
        """The 1 mV / 200 ms reference pulse every strip carries (Sprint 4.10)."""
        pulse_height_px = CALIBRATION_AMPLITUDE_MV * MM_PER_MILLIVOLT * self._pixels_per_mm
        pulse_width_px = CALIBRATION_DURATION_SECONDS * MM_PER_SECOND * self._pixels_per_mm
        left = calibration_width_px - pulse_width_px
        top = baseline_px - pulse_height_px
        path = (
            f"M0 {_format(baseline_px)}"
            f"H{_format(left)}"
            f"V{_format(top)}"
            f"H{_format(calibration_width_px)}"
            f"V{_format(baseline_px)}"
        )
        return (
            f'<path class="ecg-calibration" d="{path}" stroke="{CALIBRATION_COLOUR}" '
            'stroke-width="1.5" fill="none"/>'
        )

    def _trace(
        self,
        samples: np.ndarray,
        offset_px: float,
        trace_width_px: float,
        baseline_px: float,
    ) -> str:
        """The waveform itself, at 10 mm/mV around the baseline."""
        x = offset_px + np.linspace(0.0, trace_width_px, samples.size, endpoint=True)
        y = baseline_px - samples * MM_PER_MILLIVOLT * self._pixels_per_mm
        # Amplitudes beyond the strip are clipped rather than rescaled: the
        # gain stays standard so strips remain comparable (Sprint 4.14).
        y = np.clip(y, 0.0, self._strip_height_mm * self._pixels_per_mm)

        points = "L".join(f"{_format(px)} {_format(py)}" for px, py in zip(x, y))
        return (
            f'<path class="ecg-trace" d="M{points}" fill="none" stroke="{TRACE_COLOUR}" '
            'stroke-width="1.25" stroke-linejoin="round" stroke-linecap="round"/>'
        )

    def _labels(self, strip: RhythmStrip, width_px: float, height_px: float) -> str:
        """Lead identity and the scale the strip is drawn at."""
        return (
            f'<g class="ecg-labels" font-family="Inter, sans-serif" fill="{LABEL_COLOUR}">'
            f'<text x="{_format(2 * self._pixels_per_mm)}" '
            f'y="{_format(4 * self._pixels_per_mm)}" font-size="{_format(3 * self._pixels_per_mm)}" '
            f'font-weight="600">Lead {strip.lead}</text>'
            f'<text x="{_format(width_px - 2 * self._pixels_per_mm)}" '
            f'y="{_format(height_px - 2 * self._pixels_per_mm)}" '
            f'font-size="{_format(2.5 * self._pixels_per_mm)}" text-anchor="end">'
            f"{_format(MM_PER_SECOND)} mm/s &#183; {_format(MM_PER_MILLIVOLT)} mm/mV &#183; "
            f"{_format(strip.sampling_rate_hz)} Hz</text>"
            "</g>"
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _decimate(self, samples: np.ndarray) -> np.ndarray:
        """Reduces drawn points to what the strip can resolve (presentation only)."""
        if samples.size <= self._max_render_points:
            return samples
        stride = int(np.ceil(samples.size / self._max_render_points))
        return samples[::stride]
