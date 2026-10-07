"""Corrupted File Validation.

Purpose:
    Verify that each source file referenced by the recording still exists
    and is non-empty (Implementation Spec 11.6: "Files readable... File
    size greater than zero.").

Input:
    ParsedECG

Output:
    list[ValidationIssue]
"""

from __future__ import annotations

from app.ecg.constants import ValidationSeverity, ValidationStatus
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.validation.validation_result import ValidationIssue

_NAME = "CorruptedFilesValidator"


def check_corrupted_files(parsed: ParsedECG) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for path in parsed.source_files:
        if not path.exists():
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.FATAL,
                    status=ValidationStatus.FAIL,
                    message=f"Source file {path.name!r} is missing at validation time.",
                )
            )
            continue
        try:
            size = path.stat().st_size
        except OSError:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.FATAL,
                    status=ValidationStatus.FAIL,
                    message=f"Source file {path.name!r} could not be read.",
                )
            )
            continue
        if size == 0:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.ERROR,
                    status=ValidationStatus.FAIL,
                    message=f"Source file {path.name!r} is empty.",
                )
            )
    return issues
