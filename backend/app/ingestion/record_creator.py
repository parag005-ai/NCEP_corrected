"""Ingestion Pipeline Orchestrator.

Purpose:
    Drive one uploaded ECG recording through the complete, fixed Phase 1
    pipeline -- format detection, parsing, metadata extraction,
    validation, ECGRecord construction, artifact generation, and storage
    (Implementation Spec 3.2). This is the single entry point the service
    layer calls to ingest an upload; no stage may be skipped or reordered
    (3.14 -- Pipeline Failure: "If a stage fails, execution shall stop.").

Input:
    upload_id, the uploaded files.

Output:
    IngestionResult (ECGRecord, StorageResult)

Exceptions:
    Propagates FormatDetectionError, UnsupportedFormatError, ParserError
    subclasses, MetadataExtractionError, ValidationFailedError,
    BuilderError, and StorageError unmodified, so the caller can translate
    them into a structured API error response (7.14).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.ecg.models.ecg_record import ECGRecord
from app.ingestion.builders.ecg_record_builder import ECGRecordBuilder
from app.ingestion.detectors.format_detector import detect_format
from app.ingestion.factories.parser_factory import get_parser
from app.ingestion.metadata_extractor import MetadataOrchestrator
from app.ingestion.storage.orchestrator import StorageOrchestrator, StorageRequest, StorageResult
from app.ingestion.validator import ValidationOrchestrator


@dataclass(frozen=True)
class IngestionResult:
    """The outcome of a complete, successful ingestion run."""

    record: ECGRecord
    storage: StorageResult


def create_ecg_record(
    upload_id: str,
    files: list[Path],
    *,
    storage: StorageOrchestrator | None = None,
) -> IngestionResult:
    """Runs the full Phase 1 ingestion pipeline for one upload and returns the stored ECGRecord.

    Stage order (fixed, Implementation Spec 3.2):
        Format Detection -> Parser Factory -> Parser -> Metadata Extraction
        -> Validation -> ECGRecord Builder -> Artifact Generation -> Storage
    """
    processing_started_at = datetime.now(timezone.utc)

    source_format = detect_format(files)
    parser = get_parser(source_format)
    parsed = parser.parse(files)

    record_id = str(uuid.uuid4())
    metadata = MetadataOrchestrator.extract(parsed, record_id=record_id)

    validated = ValidationOrchestrator.validate(parsed, metadata)
    record = ECGRecordBuilder.build(validated, upload_id=upload_id)

    storage_orchestrator = storage or StorageOrchestrator()
    storage_result = storage_orchestrator.store(
        StorageRequest(
            record=record,
            upload_id=upload_id,
            source_files=tuple(files),
            validation_result=validated.validation_result,
            processing_started_at=processing_started_at,
        )
    )

    return IngestionResult(record=record, storage=storage_result)
