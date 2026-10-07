"""Standardized Output Artifact Generation.

Purpose:
    Translate a canonical ECGRecord into the standardized, storage-ready
    artifacts defined in Implementation Spec Chapter 14: a waveform
    artifact (binary + standardized CSV), one JSON artifact per metadata
    category, an annotation artifact, and a processing manifest.

Responsibilities:
    - Serialize Waveform into a compact binary artifact plus a small JSON
      descriptor (no patient information).
    - Serialize Waveform into the standardized `waveform.csv` artifact
      consumed by downstream (preprocessing/analysis) modules.
    - Serialize each metadata category into its own JSON artifact.
    - Build the ProcessingManifest recording how the recording was
      processed (traceability, never waveform samples or PHI).

Shall NOT:
    - Parse, validate, or modify the ECGRecord.
    - Perform storage I/O (that is the Storage Manager's job).

Input:
    ECGRecord, ValidationResult, upload/processing context.

Output:
    Waveform bytes (.npz + .csv) + metadata dict, per-category metadata
    dicts, ProcessingManifest.

waveform.csv schema:
    One header row followed by one row per sample, comma-separated,
    UTF-8, LF line endings:

        sample_index,time_s,<lead_1>,<lead_2>,...,<lead_n>

    - `sample_index`: 0-based integer sample position.
    - `time_s`: sample_index / sampling_rate_hz, seconds from recording
      start, 6 decimal places.
    - One column per lead actually present in the Waveform (never all 15
      canonical slots -- absent leads are omitted, not zero-filled), named
      by its canonical lead code (I, II, III, aVR, aVL, aVF, V1-V6, X, Y,
      Z) and ordered per `CANONICAL_LEAD_ORDER`. Values are physical units
      (`waveform.units`, typically mV), 6 decimal places.
"""

from __future__ import annotations

import io
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
from enum import Enum

import numpy as np

from app.ecg.constants import CANONICAL_LEAD_ORDER, ValidationStatus
from app.ecg.models.ecg_record import ECGRecord
from app.ingestion.validation.validation_result import ValidationIssue, ValidationResult

SOFTWARE_VERSION = "ncep-ingestion-1.0.0"


@dataclass(frozen=True)
class ProcessingManifest:
    """Traceability record for one ingestion run (Implementation Spec 14.9)."""

    processing_id: str
    upload_id: str
    record_id: str
    source_format: str
    parser_name: str
    validation_status: ValidationStatus
    validation_issues: tuple[ValidationIssue, ...]
    processing_started_at: datetime
    processing_completed_at: datetime
    software_version: str
    generated_artifacts: tuple[str, ...] = field(default_factory=tuple)


def to_jsonable(value):
    """Recursively convert enums/dates/tuples into plain JSON-serializable values."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


def metadata_to_dict(obj) -> dict:
    """Convert a frozen dataclass domain object into a JSON-serializable dict."""
    if not is_dataclass(obj):
        raise TypeError(f"metadata_to_dict expects a dataclass instance, got {type(obj)!r}")
    return to_jsonable(asdict(obj))


class ArtifactGenerator:
    """Generates the standardized output artifacts for one ECGRecord (Implementation Spec Chapter 14)."""

    @staticmethod
    def generate_waveform_artifact(record: ECGRecord) -> tuple[bytes, dict]:
        """Returns (compressed .npz bytes, waveform descriptor dict). No patient information."""
        waveform = record.waveform
        buffer = io.BytesIO()
        arrays = {lead.value: signal.samples for lead, signal in waveform.leads.items()}
        np.savez_compressed(buffer, **arrays)

        descriptor = {
            "sampling_rate_hz": waveform.sampling_rate_hz,
            "units": waveform.units,
            "sample_count": waveform.sample_count,
            "duration_seconds": waveform.duration_seconds,
            "available_leads": [lead.value for lead in waveform.available_leads],
            "xyz_available": waveform.xyz_available,
        }
        return buffer.getvalue(), descriptor

    @staticmethod
    def generate_waveform_csv(record: ECGRecord) -> bytes:
        """Returns the standardized `waveform.csv` artifact (see module docstring for schema)."""
        waveform = record.waveform
        leads_in_order = [lead for lead in CANONICAL_LEAD_ORDER if lead in waveform.leads]

        sample_index = np.arange(waveform.sample_count, dtype=np.float64)
        time_s = sample_index / waveform.sampling_rate_hz
        columns = [sample_index, time_s] + [waveform.leads[lead].samples for lead in leads_in_order]
        matrix = np.column_stack(columns)

        header = ",".join(["sample_index", "time_s", *(lead.value for lead in leads_in_order)])
        fmt = ["%d", "%.6f"] + ["%.6f"] * len(leads_in_order)

        buffer = io.StringIO()
        np.savetxt(buffer, matrix, delimiter=",", header=header, comments="", fmt=fmt)
        return buffer.getvalue().encode("utf-8")

    @staticmethod
    def generate_manifest(
        record: ECGRecord,
        validation_result: ValidationResult,
        upload_id: str,
        started_at: datetime,
        completed_at: datetime,
        generated_artifacts: tuple[str, ...],
    ) -> ProcessingManifest:
        return ProcessingManifest(
            processing_id=str(uuid.uuid4()),
            upload_id=upload_id,
            record_id=record.record_id,
            source_format=record.ecg_metadata.source_format.value,
            parser_name=record.source_information.parser_name,
            validation_status=validation_result.status,
            validation_issues=validation_result.issues,
            processing_started_at=started_at,
            processing_completed_at=completed_at,
            software_version=SOFTWARE_VERSION,
            generated_artifacts=generated_artifacts,
        )
