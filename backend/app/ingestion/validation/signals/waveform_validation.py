"""Waveform Validation.

Purpose:
    Verify that waveform data is structurally valid (Implementation Spec
    11.7). No signal processing is performed here.

Input:
    ParsedECG

Output:
    list[ValidationIssue]
"""

from __future__ import annotations

import numpy as np

from app.ecg.constants import ValidationSeverity, ValidationStatus
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.validation.validation_result import ValidationIssue

_NAME = "WaveformValidator"


class WaveformValidator:
    """Verifies structural validity of the parsed waveform."""

    @staticmethod
    def validate(parsed: ParsedECG) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        waveform = parsed.waveform

        if waveform.sample_count <= 0:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.FATAL,
                    status=ValidationStatus.FAIL,
                    message="Waveform contains zero samples.",
                )
            )
            return issues

        for lead, signal in waveform.leads.items():
            samples = signal.samples
            if samples.shape[0] != waveform.sample_count:
                issues.append(
                    ValidationIssue(
                        validator_name=_NAME,
                        severity=ValidationSeverity.ERROR,
                        status=ValidationStatus.FAIL,
                        message=f"Lead {lead.value} has {samples.shape[0]} samples, expected {waveform.sample_count}.",
                    )
                )
                continue

            nan_count = int(np.count_nonzero(~np.isfinite(samples)))
            if nan_count == samples.shape[0]:
                issues.append(
                    ValidationIssue(
                        validator_name=_NAME,
                        severity=ValidationSeverity.ERROR,
                        status=ValidationStatus.FAIL,
                        message=f"Lead {lead.value} contains no decodable (finite) sample values.",
                    )
                )
            elif nan_count > 0:
                issues.append(
                    ValidationIssue(
                        validator_name=_NAME,
                        severity=ValidationSeverity.WARNING,
                        status=ValidationStatus.WARNING,
                        message=f"Lead {lead.value} contains {nan_count} non-finite sample value(s).",
                        recommendation="Review the source recording for dropout or decode gaps in this lead.",
                    )
                )

        return issues
