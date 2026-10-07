"""Patient Metadata Validation.

Purpose:
    Validate patient metadata completeness (Implementation Spec 11.9).
    Missing patient information generates a WARNING, never a FAIL -- the
    ingestion pipeline shall not reject a recording solely because patient
    metadata is incomplete (Business Rule 8.6).

Input:
    PatientMetadata

Output:
    list[ValidationIssue]
"""

from __future__ import annotations

from app.ecg.constants import ValidationSeverity, ValidationStatus
from app.ecg.models.patient_metadata import PatientMetadata
from app.ingestion.validation.validation_result import ValidationIssue

_NAME = "PatientMetadataValidator"


class PatientMetadataValidator:
    """Flags incomplete patient metadata as a warning, never a failure."""

    @staticmethod
    def validate(patient_metadata: PatientMetadata) -> list[ValidationIssue]:
        missing = patient_metadata.missing_fields()
        if not missing:
            return []
        return [
            ValidationIssue(
                validator_name=_NAME,
                severity=ValidationSeverity.WARNING,
                status=ValidationStatus.WARNING,
                message=f"Patient metadata is missing field(s): {', '.join(missing)}.",
                recommendation="Complete the missing patient information through the clinical workflow.",
            )
        ]
