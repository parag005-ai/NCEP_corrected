"""The Generation Context -- single source of truth for one report generation.

Sprint 2.10 / 3.7: the Generation Context is created once, before pipeline
execution begins, and remains immutable throughout. Every downstream stage
(visualization, clinical rules, narrative, builders, template engine) reads
from it and no stage queries the database or any upstream module again during
composition (Sprint 6.5).

Immutability is real, not conventional: every object here is a frozen
dataclass, every collection is a tuple, and every parsed document is deep
frozen into read-only mappings by ``app.reporting.models.documents``.

Phase 1 (Sprint 3.15 / 5.7): the Signal Processing sections carry an explicit
``AWAITING_SIGNAL_PROCESSING`` status and a standardized placeholder instead
of fabricated values. When Signal Processing is integrated, those sections
gain a payload -- no structural change to this model, the loader, the
builders or the templates is required.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.reporting.constants import PLACEHOLDER_AWAITING_SIGNAL_PROCESSING, SectionStatus
from app.reporting.models.documents import freeze_document
from app.reporting.models.ecg_artifacts import ECGArtifactBundle

# ---------------------------------------------------------------------------
# Data-driven report sections
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextSection:
    """One report section that is either populated or explicitly unavailable.

    This is the extension point that keeps the Phase 1 placeholder strategy
    from becoming a Phase 2 migration: a section starts as
    ``AWAITING_SIGNAL_PROCESSING`` with no payload, and later carries the
    validated Signal Processing output in ``payload`` under the same name.
    """

    name: str
    status: SectionStatus
    placeholder: str | None = None
    payload: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", freeze_document(self.payload) if self.payload is not None else None)

    @property
    def is_available(self) -> bool:
        return self.status is SectionStatus.AVAILABLE

    @classmethod
    def awaiting_signal_processing(cls, name: str) -> "ContextSection":
        """A section whose data source is the not-yet-integrated Signal Processing module."""
        return cls(
            name=name,
            status=SectionStatus.AWAITING_SIGNAL_PROCESSING,
            placeholder=PLACEHOLDER_AWAITING_SIGNAL_PROCESSING,
        )

    @classmethod
    def unavailable(cls, name: str, reason: str) -> "ContextSection":
        """A section whose source ran but does not produce this output."""
        return cls(name=name, status=SectionStatus.NOT_AVAILABLE, placeholder=reason)


@dataclass(frozen=True)
class SignalProcessingOutputs:
    """The Signal Processing sections of the context (Sprint 2.10 / 3.7 / 5.14).

    Phase 1 leaves every section awaiting Signal Processing. The section names
    are exactly those the Sprint enumerates, so the Phase 2 integration layer
    populates them without renaming anything downstream.
    """

    ecg_parameters: ContextSection
    clinical_measurements: ContextSection
    signal_quality_metrics: ContextSection
    waveform_annotations: ContextSection
    beat_selection: ContextSection
    clinical_findings: ContextSection

    @classmethod
    def awaiting_signal_processing(cls) -> "SignalProcessingOutputs":
        """The Phase 1 state: every Signal Processing section is a placeholder."""
        return cls(
            ecg_parameters=ContextSection.awaiting_signal_processing("ECG Parameters"),
            clinical_measurements=ContextSection.awaiting_signal_processing("Clinical Measurements"),
            signal_quality_metrics=ContextSection.awaiting_signal_processing("Signal Quality Metrics"),
            waveform_annotations=ContextSection.awaiting_signal_processing("Waveform Annotations"),
            beat_selection=ContextSection.awaiting_signal_processing("Beat Selection Information"),
            clinical_findings=ContextSection.awaiting_signal_processing("Clinical Findings"),
        )

    @property
    def sections(self) -> tuple[ContextSection, ...]:
        """Every Signal Processing section, in report order."""
        return (
            self.ecg_parameters,
            self.clinical_measurements,
            self.signal_quality_metrics,
            self.waveform_annotations,
            self.beat_selection,
            self.clinical_findings,
        )

    @property
    def is_available(self) -> bool:
        """True once at least one Signal Processing section carries data."""
        return any(section.is_available for section in self.sections)


# ---------------------------------------------------------------------------
# Administrative context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenerationMetadata:
    """Administrative identity and provenance of one generation (Sprint 3.7).

    The report identifier is deliberately absent: the ``GeneratedReport`` row
    is created once its version and template provenance are known, so at
    context-load time only the *intended* version exists.
    """

    job_id: str
    ecg_record_id: str
    requested_by_user_id: str
    report_version: int
    generated_at: datetime
    pipeline_version: str
    schema_version: str
    software_version: str


# ---------------------------------------------------------------------------
# Upstream context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrganisationContext:
    """Hospital / tenant identity (Sprint 2.10 Organization Information)."""

    organisation_id: str
    name: str
    address: str
    contact: str


@dataclass(frozen=True)
class PatientContext:
    """Patient demographics and clinical metadata (Sprint 2.10 Patient Information).

    Only the fields a clinical report presents are carried; contact details
    are deliberately excluded so they never reach a rendered document.
    """

    patient_id: str
    name: str
    age: int | None
    gender: str
    date_of_birth: date | None
    status: str
    medical_notes: str


@dataclass(frozen=True)
class DoctorContext:
    """Referring / reporting clinician (Sprint 2.10 Doctor Information)."""

    doctor_id: str
    name: str
    speciality: str
    staff_id: str
    role: str


@dataclass(frozen=True)
class RecordingQualitySummary:
    """Signal quality summary produced by ingestion preprocessing (Sprint 2.10).

    This is the *recording* quality summary already computed and persisted by
    the ECG Ingestion pipeline. It is distinct from the Signal Processing
    ``signal_quality_metrics`` section, which stays a Phase 1 placeholder, and
    nothing here is computed by the Report Generation subsystem.
    """

    quality_score: float | None
    quality_flags: tuple[str, ...]
    beat_count: int | None
    validation_status: str | None
    validation_issues: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "validation_issues", freeze_document(tuple(self.validation_issues)))


@dataclass(frozen=True)
class ECGRecordContext:
    """The recording a report is generated for (Sprint 2.10 ECG Information)."""

    ecg_record_id: str
    canonical_record_id: str
    file_name: str
    file_type: str
    source_format: str | None
    device_source: str
    recording_date: date | None
    uploaded_at: datetime
    uploaded_by: str
    sampling_rate_hz: float | None
    lead_count: int | None
    available_leads: tuple[str, ...]
    xyz_available: bool
    duration_seconds: float | None
    sample_count: int | None
    units: str | None
    notes: str
    quality: RecordingQualitySummary


# ---------------------------------------------------------------------------
# The Generation Context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenerationContext:
    """Everything required to generate both report variants for one recording.

    Created once by the Generation Context Loader and never modified. Summary
    and Detailed reports are built from this same instance, which is what
    guarantees the two variants present identical clinical data (Sprint 2.24
    Shared Report Context).
    """

    generation: GenerationMetadata
    organisation: OrganisationContext
    patient: PatientContext
    ecg: ECGRecordContext
    artifacts: ECGArtifactBundle
    signal_processing: SignalProcessingOutputs
    #: The clinician the recording is attributed to; absent when the recording
    #: has no resolvable doctor (Sprint 3.14 recoverable failure).
    doctor: DoctorContext | None = field(default=None)
