"""Rendering policy for every ECG visualization (Sprint 4.14 Consistency).

One place defines how an ECG is drawn: paper speed, gain, grid spacing, strip
geometry, the calibration pulse and the displayed window. Centralizing them
keeps every strip -- in any report, of any type, from any recording --
directly comparable, and makes a change to the house style a single edit
rather than a hunt through renderers.

The values are the clinical conventions a printed ECG uses:

    25 mm/s horizontally, 10 mm/mV vertically
    minor grid 1 mm = 40 ms / 0.1 mV, major grid 5 mm = 200 ms / 0.5 mV
    calibration pulse 1 mV tall, 200 ms wide
"""

from __future__ import annotations

#: Bumped whenever a change here would alter a rendered visualization. Artifacts
#: are only reused across report versions when their policy version matches.
RENDERING_POLICY_VERSION = "1.0.0"

# ── Paper speed and gain ──
MM_PER_SECOND = 25.0
MM_PER_MILLIVOLT = 10.0

# ── Grid ──
MINOR_GRID_MM = 1.0
MAJOR_GRID_MM = 5.0

# ── Strip geometry ──
#: Device pixels per millimetre. SVG is resolution independent; this only sets
#: the coordinate scale of the document.
PIXELS_PER_MM = 4.0
#: Vertical extent of the strip: +/- 2 mV at 10 mm/mV.
STRIP_HEIGHT_MM = 40.0
#: Width reserved on the left for the calibration pulse.
CALIBRATION_WIDTH_MM = 10.0

# ── Calibration pulse (Sprint 4.10) ──
CALIBRATION_AMPLITUDE_MV = 1.0
CALIBRATION_DURATION_SECONDS = 0.2

# ── Displayed window (Sprint 4.8) ──
#: Length of the displayed rhythm strip. A shorter recording is shown whole.
DEFAULT_WINDOW_SECONDS = 10.0

# ── Drawing limits ──
#: Upper bound on drawn points. Beyond this the strip cannot resolve
#: additional samples, so they are decimated for display only.
MAX_RENDER_POINTS = 4000

# ── Palette ──
MINOR_GRID_COLOUR = "#f4c7cb"
MAJOR_GRID_COLOUR = "#e4909a"
TRACE_COLOUR = "#181c1c"
CALIBRATION_COLOUR = "#005c55"
LABEL_COLOUR = "#3e4947"
BACKGROUND_COLOUR = "#ffffff"

# ── Output ──
SVG_CONTENT_TYPE = "image/svg+xml"
