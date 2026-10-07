"""Missing File Validation.

Purpose:
    Verify that the recording's source files are present (Implementation
    Spec 11.6).

Input:
    ParsedECG

Output:
    list[ValidationIssue]
"""

from __future__ import annotations

from app.ecg.constants import ValidationSeverity, ValidationStatus
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.validation.validation_result import ValidationIssue

_NAME = "MissingFilesValidator"


def check_missing_files(parsed: ParsedECG) -> list[ValidationIssue]:
    if not parsed.source_files:
        return [
            ValidationIssue(
                validator_name=_NAME,
                severity=ValidationSeverity.FATAL,
                status=ValidationStatus.FAIL,
                message="No source files are associated with this recording.",
            )
        ]
    return []
