"""Exception hierarchy for the ECG Ingestion & Standardization pipeline.

Every stage of the pipeline (Chapter 3 of the Phase 1 spec) fails explicitly
by raising one of these exceptions rather than returning ambiguous results.
Failures propagate backward to the calling service layer, which is
responsible for translating them into REST error responses. No ECGRecord is
ever produced when one of these is raised.
"""

from __future__ import annotations


class IngestionError(Exception):
    """Base class for every error raised by the ingestion pipeline."""

    stage: str = "ingestion"


class FormatDetectionError(IngestionError):
    """Raised when the uploaded files cannot be identified as a supported ECG format."""

    stage = "format_detection"


class UnsupportedFormatError(FormatDetectionError):
    """Raised when the detected format has no registered parser."""


# ---------------------------------------------------------------------------
# Upload Layer errors
# ---------------------------------------------------------------------------


class UploadError(IngestionError):
    """Base class for errors raised while receiving an upload, before format detection."""

    stage = "upload"


class UploadTooLargeError(UploadError):
    """Raised when the total size of an upload exceeds the configured limit."""


class DuplicateFilenameError(UploadError):
    """Raised when an upload contains two or more files with the same name."""


# ---------------------------------------------------------------------------
# Parser errors
# ---------------------------------------------------------------------------


class ParserError(IngestionError):
    """Base class for errors raised while a format-specific parser is reading a recording."""

    stage = "parsing"


class MissingRequiredFileError(ParserError):
    """Raised when a file required to interpret the recording is absent."""


class FileReadError(ParserError):
    """Raised when a required file exists but cannot be read."""


class MalformedFileError(ParserError):
    """Raised when a file is present and readable but structurally invalid."""


class UnsupportedVersionError(ParserError):
    """Raised when a recording uses a format revision the parser does not support."""


class UnmappableLeadError(ParserError):
    """Raised when a source lead identifier cannot be mapped to a canonical NCEP lead."""


# ---------------------------------------------------------------------------
# Metadata extraction errors
# ---------------------------------------------------------------------------


class MetadataExtractionError(IngestionError):
    """Raised when mandatory ECG (recording) metadata cannot be extracted.

    Missing *patient* metadata never raises this exception -- it is a valid
    outcome that produces an empty PatientMetadata object instead.
    """

    stage = "metadata_extraction"


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class ValidationFailedError(IngestionError):
    """Raised when the ValidationResult status is FAIL and the pipeline must stop.

    Carries the ValidationResult that caused the failure so callers can
    report structured validation feedback.
    """

    stage = "validation"

    def __init__(self, message: str, validation_result: object | None = None) -> None:
        super().__init__(message)
        self.validation_result = validation_result


# ---------------------------------------------------------------------------
# Builder errors
# ---------------------------------------------------------------------------


class BuilderError(IngestionError):
    """Raised when the ECGRecord Builder receives input that has not passed validation."""

    stage = "standardization"


# ---------------------------------------------------------------------------
# Storage errors
# ---------------------------------------------------------------------------


class StorageError(IngestionError):
    """Base class for persistence failures."""

    stage = "storage"


class FileStorageError(StorageError):
    """Raised when a filesystem artifact cannot be written or read."""


class DatabaseStorageError(StorageError):
    """Raised when structured metadata cannot be persisted."""


class ManifestStorageError(StorageError):
    """Raised when the processing manifest cannot be persisted."""


__all__ = [
    "IngestionError",
    "UploadError",
    "UploadTooLargeError",
    "DuplicateFilenameError",
    "FormatDetectionError",
    "UnsupportedFormatError",
    "ParserError",
    "MissingRequiredFileError",
    "FileReadError",
    "MalformedFileError",
    "UnsupportedVersionError",
    "UnmappableLeadError",
    "MetadataExtractionError",
    "ValidationFailedError",
    "BuilderError",
    "StorageError",
    "FileStorageError",
    "DatabaseStorageError",
    "ManifestStorageError",
]
