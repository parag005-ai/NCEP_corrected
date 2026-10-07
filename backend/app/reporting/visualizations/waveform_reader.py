"""Waveform Reader (Sprint 4.5).

Reads the canonical waveform artifact ECG Ingestion produced for a recording
and returns its samples together with the acquisition facts needed to draw
them to scale.

The reader never preprocesses, filters, resamples or otherwise alters the
signal: it hands back exactly what ingestion stored. Unit normalization to
millivolts is a presentation concern owned by this engine (Sprint 2.4.4) and
is applied here, on a copy, so every visualization is drawn at a comparable
gain regardless of the source recording's units.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from app.reporting.context.generation_context import GenerationContext
from app.reporting.exceptions import WaveformReadError
from app.reporting.models.ecg_artifacts import ECGArtifactBundle

#: Multiplier converting a stored unit into millivolts, the unit every ECG
#: visualization is drawn in. Unknown units are never guessed.
_MILLIVOLT_FACTORS: Mapping[str, float] = {
    "mv": 1.0,
    "millivolt": 1.0,
    "millivolts": 1.0,
    "uv": 1e-3,
    "µv": 1e-3,
    "microvolt": 1e-3,
    "microvolts": 1e-3,
    "v": 1e3,
    "volt": 1e3,
    "volts": 1e3,
}


@dataclass(frozen=True)
class WaveformData:
    """One recording's samples, in millivolts, as stored by ingestion."""

    sampling_rate_hz: float
    source_units: str
    leads: Mapping[str, np.ndarray]

    @property
    def available_leads(self) -> tuple[str, ...]:
        return tuple(self.leads)


class WaveformReader:
    """Loads the canonical waveform artifact referenced by a Generation Context."""

    def read(self, context: GenerationContext) -> WaveformData:
        """Reads every lead of the recording the context points at.

        Raises:
            WaveformReadError: the artifact is unreadable, corrupt, or stored
                in units this engine cannot express in millivolts.
        """
        return self.read_from_artifacts(
            context.artifacts,
            ecg_record_id=context.ecg.ecg_record_id,
            fallback_sampling_rate_hz=context.ecg.sampling_rate_hz,
            fallback_units=context.ecg.units,
        )

    def read_from_artifacts(
        self,
        artifacts: ECGArtifactBundle,
        *,
        ecg_record_id: str,
        fallback_sampling_rate_hz: float | None,
        fallback_units: str | None,
    ) -> WaveformData:
        """Same as ``read``, but from an already-loaded artifact bundle directly.

        Lets a caller building the Generation Context itself (Signal
        Processing needs the waveform before the context exists to hand
        back) read the same artifact the same way, without constructing a
        throwaway context first.
        """
        path = artifacts.waveform.absolute_path
        try:
            with np.load(path, allow_pickle=False) as archive:
                leads = {name: np.asarray(archive[name], dtype=np.float64) for name in archive.files}
        except Exception as exc:  # noqa: BLE001 -- any load failure is a corrupt artifact
            raise WaveformReadError(
                f"Canonical waveform artifact for ECG record {ecg_record_id!r} could not be read: {exc}"
            ) from exc

        descriptor = artifacts.waveform_descriptor
        sampling_rate_hz = descriptor.get("sampling_rate_hz") or fallback_sampling_rate_hz
        source_units = str(descriptor.get("units") or fallback_units or "")

        return WaveformData(
            sampling_rate_hz=float(sampling_rate_hz or 0.0),
            source_units=source_units,
            leads={name: samples * self._millivolt_factor(source_units) for name, samples in leads.items()},
        )

    @staticmethod
    def _millivolt_factor(units: str) -> float:
        factor = _MILLIVOLT_FACTORS.get(units.strip().lower())
        if factor is None:
            raise WaveformReadError(
                f"Waveform units {units!r} cannot be expressed in millivolts; "
                "the visualization would be drawn at an unknown gain"
            )
        return factor
