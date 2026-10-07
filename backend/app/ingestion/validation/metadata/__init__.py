"""Metadata validation."""

from app.ecg.models.ecg_metadata import ECGMetadata
from app.ecg.models.patient_metadata import PatientMetadata
from app.ingestion.validation.metadata.patient_metadata import PatientMetadataValidator
from app.ingestion.validation.metadata.recording_metadata import RecordingMetadataValidator
from app.ingestion.validation.validation_result import ValidationIssue


class MetadataValidator:
    """Aggregates recording-metadata and patient-metadata checks (Implementation Spec 11.9)."""

    @staticmethod
    def validate(ecg_metadata: ECGMetadata, patient_metadata: PatientMetadata) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        issues += RecordingMetadataValidator.validate(ecg_metadata)
        issues += PatientMetadataValidator.validate(patient_metadata)
        return issues


__all__ = ["MetadataValidator", "patient_metadata", "recording_metadata"]
