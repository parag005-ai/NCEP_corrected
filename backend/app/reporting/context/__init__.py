"""Generation Context package (Sprint 3.6 / 3.7).

Holds the immutable Generation Context -- the single source of truth for one
report generation -- and the loader that builds it from the upstream NCEP
modules. Downstream modules should import from here rather than reaching into
individual submodules.
"""

from app.reporting.context.generation_context import (
    ContextSection,
    DoctorContext,
    ECGRecordContext,
    GenerationContext,
    GenerationMetadata,
    OrganisationContext,
    PatientContext,
    RecordingQualitySummary,
    SignalProcessingOutputs,
)
from app.reporting.context.loader import GenerationContextLoader

__all__ = [
    "ContextSection",
    "DoctorContext",
    "ECGRecordContext",
    "GenerationContext",
    "GenerationContextLoader",
    "GenerationMetadata",
    "OrganisationContext",
    "PatientContext",
    "RecordingQualitySummary",
    "SignalProcessingOutputs",
]
