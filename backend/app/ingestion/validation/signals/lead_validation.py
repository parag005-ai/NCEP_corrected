"""Lead Validation.

Purpose:
    Verify consistency of the available ECG leads (Implementation Spec
    11.8). Does not require exactly fifteen leads -- it validates whatever
    leads were actually provided, supporting standard clinical ECGs, the
    PTB Diagnostic Database, and future vendor formats alike.

Input:
    ParsedECG

Output:
    list[ValidationIssue]
"""

from __future__ import annotations

from app.ecg.constants import ValidationSeverity, ValidationStatus
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.validation.validation_result import ValidationIssue

_NAME = "LeadValidator"


class LeadValidator:
    """Verifies lead-name consistency and non-zero lead count."""

    @staticmethod
    def validate(parsed: ParsedECG) -> list[ValidationIssue]:
        waveform = parsed.waveform
        issues: list[ValidationIssue] = []

        if waveform.lead_count == 0:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.FATAL,
                    status=ValidationStatus.FAIL,
                    message="No canonical leads are present in the waveform.",
                )
            )
            return issues

        if len(waveform.available_leads) != waveform.lead_count:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.ERROR,
                    status=ValidationStatus.FAIL,
                    message="Lead count is inconsistent with the set of available leads.",
                )
            )

        return issues
