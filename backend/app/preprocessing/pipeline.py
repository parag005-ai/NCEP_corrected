"""Preprocessing Pipeline Orchestrator.

Purpose:
    Run every ingested lead through filtering, baseline correction,
    normalization, beat detection, and computed quality scoring, and
    aggregate the outcome into one PreprocessingResult -- the
    preprocessing-stage counterpart to `app.ingestion.record_creator`.

Runs entirely on the immutable `Waveform` produced by ingestion and never
modifies it: `Waveform.leads` stays the canonical, un-preprocessed signal,
and this stage's output is a separate, additional artifact rather than a
replacement (matching the immutability rule ingestion already follows for
`Waveform`/`ECGRecord`).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

import numpy as np

from app.ecg.constants import CanonicalLead
from app.ecg.models.waveform import Waveform
from app.preprocessing.baseline_correction import remove_baseline_wander
from app.preprocessing.beat_detection import BeatDetectionResult, detect_beats
from app.preprocessing.filtering import apply_filters
from app.preprocessing.normalization import z_score_normalize
from app.preprocessing.signal_quality import SignalQualityResult, assess_quality


@dataclass(frozen=True)
class LeadPreprocessingResult:
    lead: CanonicalLead
    filtered_samples: np.ndarray
    beats: BeatDetectionResult
    quality: SignalQualityResult


@dataclass(frozen=True)
class PreprocessingResult:
    """Aggregate preprocessing outcome for every lead in one Waveform."""

    leads: dict[CanonicalLead, LeadPreprocessingResult] = field(default_factory=dict)

    @property
    def beat_count(self) -> int:
        """Beat count from the lead with the most detected beats (most reliable single estimate)."""
        if not self.leads:
            return 0
        return max((r.beats.beat_count for r in self.leads.values()), default=0)

    @property
    def quality_score(self) -> float:
        """Mean quality score across leads."""
        if not self.leads:
            return 0.0
        return float(np.mean([r.quality.quality_score for r in self.leads.values()]))

    @property
    def quality_flags(self) -> tuple[str, ...]:
        """Union of every flag raised by any lead, de-duplicated, order-preserving."""
        seen: dict[str, None] = {}
        for result in self.leads.values():
            for flag in result.quality.flags:
                seen.setdefault(flag, None)
        return tuple(seen.keys())


class PreprocessingOrchestrator:
    """Runs the fixed preprocessing stage order for every lead in a Waveform."""

    @staticmethod
    def run(waveform: Waveform) -> PreprocessingResult:
        results: dict[CanonicalLead, LeadPreprocessingResult] = {}
        for lead, signal in waveform.leads.items():
            raw = signal.samples
            filtered = apply_filters(raw, waveform.sampling_rate_hz)
            filtered = remove_baseline_wander(filtered, waveform.sampling_rate_hz)
            normalized = z_score_normalize(filtered)

            beats = detect_beats(filtered, waveform.sampling_rate_hz)
            quality = assess_quality(raw, filtered, beats.beat_count, waveform.duration_seconds)

            results[lead] = LeadPreprocessingResult(
                lead=lead, filtered_samples=normalized, beats=beats, quality=quality
            )

        return PreprocessingResult(leads=results)


def _to_jsonable(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def generate_preprocessed_artifact(result: PreprocessingResult) -> bytes:
    """Serializes every lead's filtered/normalized samples into compressed .npz bytes."""
    buffer = io.BytesIO()
    arrays = {lead.value: lead_result.filtered_samples for lead, lead_result in result.leads.items()}
    np.savez_compressed(buffer, **arrays)
    return buffer.getvalue()


def generate_preprocessing_report(result: PreprocessingResult) -> dict:
    """Serializes the per-lead beat/quality findings into a JSON-ready report."""
    return _to_jsonable(
        {
            "beat_count": result.beat_count,
            "quality_score": result.quality_score,
            "quality_flags": result.quality_flags,
            "leads": {
                lead.value: {
                    "beat_count": lead_result.beats.beat_count,
                    "r_peak_indices": lead_result.beats.r_peak_indices,
                    "mean_heart_rate_bpm": lead_result.beats.mean_heart_rate_bpm,
                    "quality_score": lead_result.quality.quality_score,
                    "quality_flags": lead_result.quality.flags,
                }
                for lead, lead_result in result.leads.items()
            },
        }
    )
