"""Quality Metadata Extractor.

Purpose:
    Extract quality indicators that already exist in the source recording
    (Implementation Spec 12.11). Never computes new quality metrics.

Input:
    ParsedECG

Output:
    QualityMetadata
"""

from __future__ import annotations

from app.ecg.models.quality_metadata import QualityMetadata
from app.ingestion.metadata._coercion import parse_float
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG


def _as_tuple(value) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value)


class QualityMetadataExtractor:
    """Extracts QualityMetadata from a ParsedECG's raw quality info."""

    @staticmethod
    def extract(parsed: ParsedECG) -> QualityMetadata:
        info = parsed.raw_quality_info
        return QualityMetadata(
            quality_flags=_as_tuple(info.get("quality_flags")),
            noise_indicators=_as_tuple(info.get("noise_indicators")),
            device_warnings=_as_tuple(info.get("device_warnings")),
            recording_confidence=parse_float(info.get("recording_confidence")),
        )
