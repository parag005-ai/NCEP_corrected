"""Validation Orchestrator.

Purpose:
    Run every independent validator against a ParsedECG and its extracted
    metadata, aggregate the outcome, and produce a ValidatedParsedECG --
    the only object the ECGRecord Builder is allowed to accept
    (Implementation Spec Chapter 11, 7.8, 13.8).

Responsibilities:
    - Execute Format, File, Signal (waveform/lead/sampling), Metadata
      (recording/patient), and Quality validators independently.
    - Aggregate their findings into one ValidationResult.
    - Stop the pipeline (raise) when the aggregate status is FAIL.
    - Allow the pipeline to continue when the aggregate status is
      PASS or WARNING (Validation Rule 11.14 Rule 5).

Shall NOT:
    - Modify ParsedECG or any metadata object.
    - Repair, interpolate, or fabricate data.

Input:
    ParsedECG, ExtractedMetadata

Output:
    ValidatedParsedECG

Exceptions:
    ValidationFailedError -- raised when the aggregate status is FAIL.
"""

from __future__ import annotations

from app.ingestion.exceptions import ValidationFailedError
from app.ingestion.metadata_extractor import ExtractedMetadata
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.validation.files import FileValidator
from app.ingestion.validation.format import FormatValidator
from app.ingestion.validation.metadata import MetadataValidator
from app.ingestion.validation.quality import QualityValidator
from app.ingestion.validation.signals import SignalValidator
from app.ingestion.validation.validation_result import (
    ValidatedParsedECG,
    ValidationIssue,
    ValidationResult,
    aggregate_status,
)


class ValidationOrchestrator:
    """Coordinates all independent validators and produces a ValidatedParsedECG."""

    @staticmethod
    def validate(parsed: ParsedECG, metadata: ExtractedMetadata) -> ValidatedParsedECG:
        issues: list[ValidationIssue] = []
        issues += FormatValidator.validate(parsed)
        issues += FileValidator.validate(parsed)
        issues += SignalValidator.validate(parsed)
        issues += MetadataValidator.validate(metadata.ecg, metadata.patient)
        issues += QualityValidator.validate(metadata.quality)

        result = ValidationResult(status=aggregate_status(issues), issues=tuple(issues))

        if not result.is_valid:
            raise ValidationFailedError(
                f"ECG recording failed validation with {len(result.issues)} issue(s).", validation_result=result
            )

        return ValidatedParsedECG(parsed=parsed, metadata=metadata, validation_result=result)
