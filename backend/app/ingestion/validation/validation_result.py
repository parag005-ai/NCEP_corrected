"""Validation result contracts.

Purpose:
    Define the structured outcome every validator reports (Implementation
    Spec 11.12-11.13) and the ValidatedParsedECG wrapper that is the only
    object the ECGRecord Builder is allowed to accept (13.8: "Only
    validated data may enter the builder.").
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ecg.constants import ValidationSeverity, ValidationStatus
from app.ingestion.metadata_extractor import ExtractedMetadata
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG


@dataclass(frozen=True)
class ValidationIssue:
    """A single validator's finding."""

    validator_name: str
    severity: ValidationSeverity
    status: ValidationStatus
    message: str
    recommendation: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """The aggregate outcome of running every validator (11.13)."""

    status: ValidationStatus
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return self.status != ValidationStatus.FAIL


@dataclass(frozen=True)
class ValidatedParsedECG:
    """The only input contract the ECGRecord Builder accepts (13.8)."""

    parsed: ParsedECG
    metadata: ExtractedMetadata
    validation_result: ValidationResult


def aggregate_status(issues: list[ValidationIssue]) -> ValidationStatus:
    """Aggregate PASS/WARNING/FAIL from a set of issues (11.12): FAIL beats WARNING beats PASS."""
    if any(issue.status == ValidationStatus.FAIL for issue in issues):
        return ValidationStatus.FAIL
    if any(issue.status == ValidationStatus.WARNING for issue in issues):
        return ValidationStatus.WARNING
    return ValidationStatus.PASS
