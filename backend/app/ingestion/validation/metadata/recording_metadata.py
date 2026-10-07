"""ECG (Recording) Metadata Validation.

Purpose:
    Verify mandatory recording metadata is present and sane
    (Implementation Spec 11.9). Missing ECGMetadata is a hard failure --
    unlike patient metadata, it is required for every valid ECGRecord
    (Business Rule 8.7).

Input:
    ECGMetadata

Output:
    list[ValidationIssue]
"""

from __future__ import annotations

from app.ecg.constants import ValidationSeverity, ValidationStatus
from app.ecg.models.ecg_metadata import ECGMetadata
from app.ingestion.validation.validation_result import ValidationIssue

_NAME = "RecordingMetadataValidator"


class RecordingMetadataValidator:
    """Verifies mandatory ECGMetadata fields are present and valid."""

    @staticmethod
    def validate(ecg_metadata: ECGMetadata) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if ecg_metadata.sampling_rate_hz <= 0:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.FATAL,
                    status=ValidationStatus.FAIL,
                    message="Sampling rate is missing or unavailable.",
                )
            )
        if ecg_metadata.recording_duration_seconds <= 0:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.FATAL,
                    status=ValidationStatus.FAIL,
                    message="Recording duration is missing or unavailable.",
                )
            )
        if ecg_metadata.sample_count <= 0:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.FATAL,
                    status=ValidationStatus.FAIL,
                    message="Sample count is missing or unavailable.",
                )
            )
        if not ecg_metadata.record_id:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.FATAL,
                    status=ValidationStatus.FAIL,
                    message="Record identifier is missing.",
                )
            )

        return issues
