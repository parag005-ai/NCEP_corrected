"""Format Validation.

Purpose:
    Verify that the parsed recording belongs to a supported ECG format
    with a registered parser (Implementation Spec 11.5).

Input:
    ParsedECG

Output:
    list[ValidationIssue]
"""

from __future__ import annotations

from app.ecg.constants import SUPPORTED_FORMATS, ValidationSeverity, ValidationStatus
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.validation.validation_result import ValidationIssue

_NAME = "FormatValidator"


class FormatValidator:
    """Verifies the ParsedECG's source format is supported."""

    @staticmethod
    def validate(parsed: ParsedECG) -> list[ValidationIssue]:
        if parsed.source_format not in SUPPORTED_FORMATS:
            return [
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.FATAL,
                    status=ValidationStatus.FAIL,
                    message=f"Format {parsed.source_format!r} is not a supported ECG format.",
                )
            ]
        return []
