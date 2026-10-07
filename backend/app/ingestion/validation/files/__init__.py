"""File-level validation."""

from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.validation.files.corrupted_files import check_corrupted_files
from app.ingestion.validation.files.missing_files import check_missing_files
from app.ingestion.validation.validation_result import ValidationIssue


class FileValidator:
    """Aggregates missing-file and corrupted-file checks (Implementation Spec 11.6)."""

    @staticmethod
    def validate(parsed: ParsedECG) -> list[ValidationIssue]:
        issues = check_missing_files(parsed)
        if issues:
            # No point checking individual file integrity if none are present at all.
            return issues
        return check_corrupted_files(parsed)


__all__ = ["FileValidator", "corrupted_files", "missing_files"]
