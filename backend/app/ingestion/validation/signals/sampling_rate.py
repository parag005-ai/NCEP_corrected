"""Sampling Rate / Recording Consistency Validation.

Purpose:
    Ensure the recording is internally consistent: sampling rate matches
    waveform duration, and the number of samples is consistent
    (Implementation Spec 11.10).

Input:
    ParsedECG

Output:
    list[ValidationIssue]
"""

from __future__ import annotations

import math

from app.ecg.constants import ValidationSeverity, ValidationStatus
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.validation.validation_result import ValidationIssue

_NAME = "SamplingRateValidator"
_RELATIVE_TOLERANCE = 1e-6


class SamplingRateValidator:
    """Verifies sampling rate, sample count, and duration agree with one another."""

    @staticmethod
    def validate(parsed: ParsedECG) -> list[ValidationIssue]:
        waveform = parsed.waveform
        issues: list[ValidationIssue] = []

        if waveform.sampling_rate_hz <= 0:
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.FATAL,
                    status=ValidationStatus.FAIL,
                    message="Sampling rate must be a positive value.",
                )
            )
            return issues

        expected_duration = waveform.sample_count / waveform.sampling_rate_hz
        if not math.isclose(expected_duration, waveform.duration_seconds, rel_tol=_RELATIVE_TOLERANCE):
            issues.append(
                ValidationIssue(
                    validator_name=_NAME,
                    severity=ValidationSeverity.ERROR,
                    status=ValidationStatus.FAIL,
                    message="Recording duration is inconsistent with sample count and sampling rate.",
                )
            )

        return issues
