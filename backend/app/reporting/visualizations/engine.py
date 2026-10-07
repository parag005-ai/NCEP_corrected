"""ECG Visualization Engine (Sprint 4.3 / 4.4).

    Generation Context -> Waveform Reader -> Signal Validator -> Lead Selector
                       -> Window Selector -> SVG Renderer -> Artifact Storage

Turns the canonical waveform of a recording into a report-ready rhythm strip.
It performs no clinical interpretation, annotates no beats, calculates no
parameters and never modifies waveform data (Sprint 4.14).

When the recording cannot be drawn faithfully -- no usable lead, no valid
samples -- the engine returns an explicit "unavailable" result with the reason
instead of an approximated image, and the report section carries a placeholder
(Sprint 4.6 / 4.7 / 4.14 No Fabrication Policy). Failures that mean the
artifact itself is broken (unreadable or corrupt waveform, a renderer that
cannot produce output) are raised: they are critical (Sprint 4.20).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.reporting.constants import ArtifactType
from app.reporting.context.generation_context import GenerationContext
from app.reporting.models.pending_artifact import PendingReportArtifact
from app.reporting.storage.artifact_store import ReportArtifactStore
from app.reporting.visualizations.rendering_policy import (
    DEFAULT_WINDOW_SECONDS,
    RENDERING_POLICY_VERSION,
    SVG_CONTENT_TYPE,
)
from app.reporting.visualizations.selection import select_lead, select_window, validate_signal
from app.reporting.visualizations.svg_renderer import RawECGSVGRenderer, RhythmStrip
from app.reporting.visualizations.waveform_reader import WaveformReader

logger = logging.getLogger(__name__)

VISUALIZATION_TYPE_RAW_ECG = "RAW_ECG"


@dataclass(frozen=True)
class VisualizationResult:
    """Either a stored visualization, or the reason there is none."""

    artifact: PendingReportArtifact | None = None
    unavailable_reason: str | None = None

    @property
    def is_available(self) -> bool:
        return self.artifact is not None

    @classmethod
    def unavailable(cls, reason: str) -> "VisualizationResult":
        return cls(unavailable_reason=reason)


class ECGVisualizationEngine:
    """Produces the raw ECG rhythm strip for one report generation."""

    def __init__(
        self,
        store: ReportArtifactStore,
        *,
        reader: WaveformReader | None = None,
        renderer: RawECGSVGRenderer | None = None,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self._store = store
        self._reader = reader or WaveformReader()
        self._renderer = renderer or RawECGSVGRenderer()
        self._window_seconds = window_seconds

    def generate_raw_ecg(self, context: GenerationContext, *, job_id: str) -> VisualizationResult:
        """Renders and stores the raw ECG visualization for a recording.

        Raises:
            WaveformReadError: the waveform artifact is unreadable or corrupt.
            SVGRenderingError: the strip could not be drawn.
            ReportArtifactStorageError: the SVG could not be stored.
        """
        waveform = self._reader.read(context)

        validation = validate_signal(waveform.sampling_rate_hz, waveform.leads)
        if not validation.is_usable:
            return self._unavailable(context, validation.reason or "the recording is not drawable")

        lead = select_lead(waveform.leads)
        if lead is None:
            return self._unavailable(context, "no lead carries a usable signal")

        samples = waveform.leads[lead]
        window = select_window(
            samples.size, waveform.sampling_rate_hz, window_seconds=self._window_seconds
        )

        svg = self._renderer.render(
            RhythmStrip(
                lead=lead,
                samples=samples[window.start_index : window.end_index],
                sampling_rate_hz=waveform.sampling_rate_hz,
                start_second=window.start_second,
            )
        )

        stored = self._store.write(
            ecg_record_id=context.ecg.ecg_record_id,
            job_id=job_id,
            relative_path=f"visualizations/raw_ecg_lead_{lead}.svg",
            data=svg,
        )
        logger.info(
            "raw ECG visualization generated job_id=%s ecg_record_id=%s lead=%s "
            "window=%.3f-%.3fs bytes=%s",
            job_id,
            context.ecg.ecg_record_id,
            lead,
            window.start_second,
            window.end_second,
            stored.file_size_bytes,
        )

        return VisualizationResult(
            artifact=PendingReportArtifact(
                artifact_type=ArtifactType.RAW_ECG_SVG,
                content_type=SVG_CONTENT_TYPE,
                storage_location=stored.relative_path,
                absolute_path=stored.absolute_path,
                file_size_bytes=stored.file_size_bytes,
                checksum_sha256=stored.checksum_sha256,
                generated_at=datetime.now(timezone.utc),
                artifact_metadata={
                    "visualization_type": VISUALIZATION_TYPE_RAW_ECG,
                    "policy_version": RENDERING_POLICY_VERSION,
                    "ecg_record_id": context.ecg.ecg_record_id,
                    "lead": lead,
                    "window_start_second": window.start_second,
                    "window_end_second": window.end_second,
                    "sampling_rate_hz": waveform.sampling_rate_hz,
                    "source_units": waveform.source_units,
                },
            )
        )

    @staticmethod
    def _unavailable(context: GenerationContext, reason: str) -> VisualizationResult:
        logger.info(
            "raw ECG visualization unavailable ecg_record_id=%s reason=%s",
            context.ecg.ecg_record_id,
            reason,
        )
        return VisualizationResult.unavailable(reason)
