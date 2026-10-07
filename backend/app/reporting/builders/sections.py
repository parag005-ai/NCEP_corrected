"""The structured report document a builder produces (Sprint 6.6 / 6.10).

A built report is data, not markup. Builders emit sections, values and figure
references; the Template Engine is the only component that knows what a
report looks like. That separation is what lets a template change without
touching composition, and composition change without touching templates
(Sprint 6.15).

Every value carries its own availability. A value that is missing says so
explicitly, with the standardized placeholder text a template renders in its
place -- it is never silently blank and never estimated (Sprint 3.15 / 6.16
No Fabrication Policy).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.reporting.constants import (
    PLACEHOLDER_AWAITING_SIGNAL_PROCESSING,
    PLACEHOLDER_NOT_AVAILABLE,
    ArtifactType,
    ReportType,
)
from app.reporting.models.documents import freeze_document


class SectionId(str, Enum):
    """Every section a report may contain.

    The set and order mirror the canonical Detailed Report specification
    (``index.html``), grouped by the page each section appears on. The Summary
    variant selects a subset; no section is invented outside the specification.
    """

    # Page 1 -- Executive Clinical Summary
    REPORT_HEADER = "REPORT_HEADER"
    PATIENT_INFORMATION = "PATIENT_INFORMATION"
    DOCTOR_INFORMATION = "DOCTOR_INFORMATION"
    INTERPRETATION = "INTERPRETATION"
    DOMAIN_EVIDENCE_SUMMARY = "DOMAIN_EVIDENCE_SUMMARY"
    CONFIDENCE_SUMMARY = "CONFIDENCE_SUMMARY"

    # Page 2 -- Recording & Signal Integrity
    RECORDING_ACCEPTANCE = "RECORDING_ACCEPTANCE"
    ACQUISITION_METRICS = "ACQUISITION_METRICS"
    RECORDING_SUMMARY = "RECORDING_SUMMARY"
    RAW_ECG_VISUALIZATION = "RAW_ECG_VISUALIZATION"
    LEAD_QUALITY = "LEAD_QUALITY"
    RECORDING_NOTE = "RECORDING_NOTE"
    SIGNAL_QUALITY = "SIGNAL_QUALITY"

    # Page 3 -- Standard ECG Assessment
    RHYTHM_METRICS = "RHYTHM_METRICS"
    STANDARD_ECG_MEASUREMENTS = "STANDARD_ECG_MEASUREMENTS"
    BEAT_VISUALIZATION = "BEAT_VISUALIZATION"
    STANDARD_ECG_INTERPRETATION = "STANDARD_ECG_INTERPRETATION"

    # Page 4 -- Atrial Electrophysiology
    ATRIAL_VISUALIZATION = "ATRIAL_VISUALIZATION"
    ATRIAL_CRITERIA = "ATRIAL_CRITERIA"
    ATRIAL_MEASUREMENTS = "ATRIAL_MEASUREMENTS"
    ATRIAL_INTERPRETATION = "ATRIAL_INTERPRETATION"

    # Page 5 -- Ventricular Electrophysiology (SAECG)
    VLP_VERDICT = "VLP_VERDICT"
    SAECG_PROCESSING = "SAECG_PROCESSING"
    SAECG_VISUALIZATION = "SAECG_VISUALIZATION"
    SAECG_PARAMETERS = "SAECG_PARAMETERS"
    VENTRICULAR_INTERPRETATION = "VENTRICULAR_INTERPRETATION"

    # Page 6 -- Repolarization Analysis
    REPOLARIZATION_TIMING = "REPOLARIZATION_TIMING"
    REPOLARIZATION_VISUALIZATION = "REPOLARIZATION_VISUALIZATION"
    REPOLARIZATION_ANALYSIS = "REPOLARIZATION_ANALYSIS"
    REPOLARIZATION_INTERPRETATION = "REPOLARIZATION_INTERPRETATION"

    # Page 7 -- Integrated Clinical Assessment
    INTEGRATED_ASSESSMENT = "INTEGRATED_ASSESSMENT"
    EVIDENCE_LEDGER = "EVIDENCE_LEDGER"
    CLINICAL_FINDINGS = "CLINICAL_FINDINGS"
    CLINICAL_MEASUREMENTS = "CLINICAL_MEASUREMENTS"
    CLINICAL_FLAGS = "CLINICAL_FLAGS"
    RECOMMENDATIONS = "RECOMMENDATIONS"
    CLINICAL_REVIEW = "CLINICAL_REVIEW"

    # Page 8 -- Technical Appendix
    TRACEABILITY_CHAIN = "TRACEABILITY_CHAIN"
    ACQUISITION_RECORD = "ACQUISITION_RECORD"
    PROCESSING_RECORD = "PROCESSING_RECORD"
    SOFTWARE_RECORD = "SOFTWARE_RECORD"
    REPORT_PROVENANCE = "REPORT_PROVENANCE"
    METHOD_PROVENANCE = "METHOD_PROVENANCE"

    # Present on every page
    PAGE_TAKEAWAYS = "PAGE_TAKEAWAYS"
    REPORT_FOOTER = "REPORT_FOOTER"


class Availability(str, Enum):
    """Why a value or section does or does not carry data."""

    AVAILABLE = "AVAILABLE"
    #: The data source exists but holds nothing for this recording.
    NOT_AVAILABLE = "NOT_AVAILABLE"
    #: The data source is the Signal Processing module, not yet integrated.
    AWAITING_SIGNAL_PROCESSING = "AWAITING_SIGNAL_PROCESSING"


@dataclass(frozen=True)
class ReportValue:
    """One labelled datum of a report section."""

    label: str
    value: str | None = None
    unit: str | None = None
    reference: str | None = None
    availability: Availability = Availability.AVAILABLE
    placeholder: str | None = None

    @property
    def is_available(self) -> bool:
        return self.availability is Availability.AVAILABLE

    @property
    def display_value(self) -> str:
        """What a template shows: the value, or its standardized placeholder."""
        if self.is_available and self.value is not None:
            return self.value
        return self.placeholder or PLACEHOLDER_NOT_AVAILABLE


@dataclass(frozen=True)
class ReportFigure:
    """A generated image a section presents, referenced never embedded.

    The bytes stay in the artifact store; the Template Engine resolves the
    reference when it renders (Sprint 4.17).
    """

    caption: str
    artifact_type: ArtifactType
    storage_location: str
    absolute_path: str
    media_type: str
    figure_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "figure_metadata", freeze_document(dict(self.figure_metadata)))


@dataclass(frozen=True)
class ReportSection:
    """One logical section of a report, built independently (Sprint 6.6)."""

    id: SectionId
    title: str
    availability: Availability = Availability.AVAILABLE
    values: tuple[ReportValue, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    figures: tuple[ReportFigure, ...] = field(default_factory=tuple)
    placeholder: str | None = None

    @property
    def is_available(self) -> bool:
        return self.availability is Availability.AVAILABLE

    @property
    def display_placeholder(self) -> str:
        return self.placeholder or PLACEHOLDER_NOT_AVAILABLE

    def value(self, label: str) -> ReportValue | None:
        """The value with this label, or None when the section does not carry it."""
        for value in self.values:
            if value.label == label:
                return value
        return None

    def display(self, label: str) -> str:
        """What a template shows for a label, falling back to the section placeholder."""
        value = self.value(label)
        return value.display_value if value is not None else self.display_placeholder

    @classmethod
    def awaiting_signal_processing(cls, section_id: SectionId, title: str) -> "ReportSection":
        """A section whose data source is the not-yet-integrated Signal Processing module.

        The section stays in the report and keeps its place in the layout; only
        its content is a placeholder (Sprint 5.7 / 6.16).
        """
        return cls(
            id=section_id,
            title=title,
            availability=Availability.AWAITING_SIGNAL_PROCESSING,
            placeholder=PLACEHOLDER_AWAITING_SIGNAL_PROCESSING,
        )

    @classmethod
    def unavailable(cls, section_id: SectionId, title: str, reason: str) -> "ReportSection":
        """A section whose data is absent for a reason other than Signal Processing."""
        return cls(
            id=section_id,
            title=title,
            availability=Availability.NOT_AVAILABLE,
            placeholder=reason,
        )


@dataclass(frozen=True)
class ReportDocumentMetadata:
    """Traceability metadata every generated report embeds (Sprint 6.18).

    The report identifier and template identity are deliberately absent: they
    are known once the ``GeneratedReport`` row exists, which the Template
    Engine creates when it renders. Everything here is known at build time.
    """

    ecg_record_id: str
    job_id: str
    report_version: int
    generated_at: datetime
    pipeline_version: str
    schema_version: str
    software_version: str


@dataclass(frozen=True)
class ReportDocument:
    """A complete report as structured data, ready to be bound to a template."""

    report_type: ReportType
    title: str
    metadata: ReportDocumentMetadata
    sections: tuple[ReportSection, ...]

    def section(self, section_id: SectionId) -> ReportSection | None:
        """The section with this id, or None when the variant omits it."""
        for section in self.sections:
            if section.id is section_id:
                return section
        return None

    @property
    def section_ids(self) -> tuple[SectionId, ...]:
        return tuple(section.id for section in self.sections)
