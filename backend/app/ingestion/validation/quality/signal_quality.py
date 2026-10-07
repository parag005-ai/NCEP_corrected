"""Quality Validation.

Purpose:
    Preserve and surface quality indicators already present in the source
    recording (Implementation Spec 11.11). Never computes new quality
    metrics.

Input:
    QualityMetadata

Output:
    list[ValidationIssue]
"""

from __future__ import annotations

from app.ecg.constants import ValidationSeverity, ValidationStatus
from app.ecg.models.quality_metadata import QualityMetadata
from app.ingestion.validation.validation_result import ValidationIssue

_NAME = "QualityValidator"


class QualityValidator:
    """Surfaces existing device/quality warnings as informational validation issues."""

    @staticmethod
    def validate(quality_metadata: QualityMetadata) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for flag in quality_metadata.device_warnings:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.WARNING,
                    status=ValidationStatus.WARNING,
                    message=f"Source recording reported a device warning: {flag}.",
                )
            )
        for indicator in quality_metadata.noise_indicators:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.INFO,
                    status=ValidationStatus.WARNING,
                    message=f"Source recording reported a noise indicator: {indicator}.",
                )
            )
        return issues
