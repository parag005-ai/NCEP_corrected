"""Signal validation."""

from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.validation.signals.lead_validation import LeadValidator
from app.ingestion.validation.signals.sampling_rate import SamplingRateValidator
from app.ingestion.validation.signals.waveform_validation import WaveformValidator
from app.ingestion.validation.validation_result import ValidationIssue


class SignalValidator:
    """Aggregates waveform, lead, and sampling-rate consistency checks (Implementation Spec 11.7-11.10)."""

    @staticmethod
    def validate(parsed: ParsedECG) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        issues += WaveformValidator.validate(parsed)
        issues += LeadValidator.validate(parsed)
        issues += SamplingRateValidator.validate(parsed)
        return issues


__all__ = ["SignalValidator", "lead_validation", "sampling_rate", "waveform_validation"]
