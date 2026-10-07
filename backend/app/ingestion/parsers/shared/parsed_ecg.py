"""ParsedECG: the internal contract between a format-specific parser and the
Metadata Framework / Validation Framework (Implementation Spec,
"Architectural Refinement -- ParsedECG Introduction").

ParsedECG is never exposed outside the ingestion subsystem, never stored as
the canonical representation, and never consumed by preprocessing or
analysis modules. Every parser produces exactly one ParsedECG per
recording.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.ecg.constants import ECGFormat
from app.ecg.models.annotations import Annotation
from app.ecg.models.waveform import Waveform


@dataclass(frozen=True)
class ParsedECG:
    """Raw parsed output of a format-specific parser, prior to metadata extraction and validation."""

    source_format: ECGFormat
    source_files: tuple[Path, ...]
    parser_name: str
    waveform: Waveform

    # Raw, format-specific key/value bags. Metadata extractors (Chapter 12)
    # interpret these into structured PatientMetadata / ECGMetadata /
    # ClinicalMetadata / DeviceMetadata / QualityMetadata objects. Keys are
    # extractor-defined logical field names, not source-format field names,
    # so extractors stay parser-agnostic wherever the parser can normalize
    # cheaply (e.g. "patient_id" rather than a DICOM tag number).
    raw_patient_info: dict[str, Any] = field(default_factory=dict)
    raw_recording_info: dict[str, Any] = field(default_factory=dict)
    raw_clinical_info: dict[str, Any] = field(default_factory=dict)
    raw_device_info: dict[str, Any] = field(default_factory=dict)
    raw_quality_info: dict[str, Any] = field(default_factory=dict)
    raw_annotations: tuple[Annotation, ...] = field(default_factory=tuple)
