"""Independent section builders (Sprint 6.6 / 6.15).

One builder per logical section, each receiving only what its section needs.
Both report variants draw on the same builders, which is what guarantees the
Summary and the Detailed report state identical facts -- they differ in which
sections they include and how much of each they show, never in the data
itself (Sprint 2.24 Shared Report Context).

Nothing here computes a clinical value. Sections whose data source is the
Signal Processing module are emitted as placeholders that keep their place in
the layout (Sprint 5.7 / 6.16), and every value that is simply absent says so
rather than showing an invented one.
"""

from __future__ import annotations

from datetime import date, datetime

from app.reporting.constants import PLACEHOLDER_AWAITING_SIGNAL_PROCESSING, ReportType
from app.reporting.context.generation_context import ContextSection, GenerationContext
from app.reporting.models.pending_artifact import PendingReportArtifact
from app.reporting.builders.sections import (
    Availability,
    ReportFigure,
    ReportSection,
    ReportValue,
    SectionId,
)

# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------


def _text(value: str | None) -> str | None:
    """Normalizes an upstream free-text field: blank is absent, not empty."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _number(value: float | int | None, *, decimals: int = 0) -> str | None:
    if value is None:
        return None
    if isinstance(value, int) or decimals == 0:
        return f"{round(value):,}"
    return f"{value:.{decimals}f}"


def _duration(seconds: float | None) -> str | None:
    """Recording length as mm:ss, the form the specification displays."""
    if seconds is None:
        return None
    total = int(round(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def _moment(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y %H:%M UTC")
    return value.strftime("%d %b %Y")


def value_of(
    label: str,
    value: str | None,
    *,
    unit: str | None = None,
    reference: str | None = None,
) -> ReportValue:
    """A datum that is present, or explicitly absent when the source holds nothing."""
    if value is None:
        return ReportValue(label=label, availability=Availability.NOT_AVAILABLE, unit=unit)
    return ReportValue(label=label, value=value, unit=unit, reference=reference)


def awaiting_signal_processing(label: str, *, unit: str | None = None) -> ReportValue:
    """A datum the Signal Processing module will supply (Sprint 5.7)."""
    return ReportValue(
        label=label,
        unit=unit,
        availability=Availability.AWAITING_SIGNAL_PROCESSING,
        placeholder=PLACEHOLDER_AWAITING_SIGNAL_PROCESSING,
    )


SP_VALUE_NOT_PRODUCED = "Not produced by Signal Processing"
CLINICAL_RULES_NOT_CONFIGURED = "Clinical result unavailable: approved decision limits are not configured"
ANNOTATION_NOT_PRODUCED = "Waveform annotation is not produced by Signal Processing"


def unavailable_value(
    label: str, reason: str = SP_VALUE_NOT_PRODUCED, *, unit: str | None = None
) -> ReportValue:
    """A value the completed SP result did not produce.

    This is deliberately distinct from ``awaiting_signal_processing``: the
    analysis ran, but its authoritative result has no value for this field.
    """
    return ReportValue(
        label=label,
        unit=unit,
        availability=Availability.NOT_AVAILABLE,
        placeholder=reason,
    )


# ---------------------------------------------------------------------------
# Sections available in Phase 1
# ---------------------------------------------------------------------------


def build_header_section(context: GenerationContext, variant: ReportType) -> ReportSection:
    """Report identity and the organisation it was produced for."""
    title = "Clinical Summary Report" if variant is ReportType.SUMMARY else "Clinical Diagnostic Report"
    return ReportSection(
        id=SectionId.REPORT_HEADER,
        title=title,
        values=(
            value_of("Organisation", _text(context.organisation.name)),
            value_of("Report version", str(context.generation.report_version)),
            value_of("Generated", _moment(context.generation.generated_at)),
            value_of("ECG record", context.ecg.ecg_record_id),
        ),
    )


def build_patient_section(context: GenerationContext, variant: ReportType) -> ReportSection:
    """Patient demographics; the Detailed variant adds clinical context (Sprint 6.7 / 6.8)."""
    patient = context.patient
    values = [
        value_of("Patient ID", patient.patient_id),
        value_of("Name", _text(patient.name)),
        value_of("Age", _number(patient.age), unit="years"),
        value_of("Gender", _text(patient.gender)),
    ]
    if variant is ReportType.DETAILED:
        values += [
            value_of("Date of birth", _moment(patient.date_of_birth)),
            value_of("Clinical status", _text(patient.status)),
            value_of("Clinical notes", _text(patient.medical_notes)),
        ]
    return ReportSection(
        id=SectionId.PATIENT_INFORMATION, title="Patient Information", values=tuple(values)
    )


def build_doctor_section(context: GenerationContext, variant: ReportType) -> ReportSection:
    """The reporting clinician, or an explicit note that none is on record.

    An unresolvable doctor is a recoverable gap (Sprint 3.14), so the section
    stays in the layout and states that the information is unavailable.
    """
    doctor = context.doctor
    if doctor is None:
        return ReportSection.unavailable(
            SectionId.DOCTOR_INFORMATION,
            "Referring Clinician",
            "No clinician is recorded for this recording",
        )

    values = [
        value_of("Name", _text(doctor.name)),
        value_of("Speciality", _text(doctor.speciality)),
    ]
    if variant is ReportType.DETAILED:
        values += [
            value_of("Staff ID", _text(doctor.staff_id)),
            value_of("Role", _text(doctor.role)),
            value_of("Organisation", _text(context.organisation.name)),
        ]
    return ReportSection(
        id=SectionId.DOCTOR_INFORMATION, title="Referring Clinician", values=tuple(values)
    )


def build_recording_section(context: GenerationContext, variant: ReportType) -> ReportSection:
    """How the recording was acquired (Sprint 6.7 Recording Summary)."""
    ecg = context.ecg
    values = [
        value_of("Recording date", _moment(ecg.recording_date)),
        value_of("Duration", _number(ecg.duration_seconds, decimals=1), unit="s"),
        value_of("Sampling rate", _number(ecg.sampling_rate_hz), unit="Hz"),
        value_of("Leads", ", ".join(ecg.available_leads) if ecg.available_leads else None),
    ]
    if variant is ReportType.DETAILED:
        values += [
            value_of("Lead count", _number(ecg.lead_count)),
            value_of("Samples", _number(ecg.sample_count)),
            value_of("Amplitude units", _text(ecg.units)),
            value_of("Source format", _text(ecg.source_format) or _text(ecg.file_type)),
            value_of("Device", _text(ecg.device_source)),
            value_of("Source file", _text(ecg.file_name)),
            value_of("Uploaded", _moment(ecg.uploaded_at)),
            value_of("Uploaded by", _text(ecg.uploaded_by)),
            value_of("Recording notes", _text(ecg.notes)),
        ]
    return ReportSection(
        id=SectionId.RECORDING_SUMMARY, title="Recording Summary", values=tuple(values)
    )


def build_signal_quality_section(context: GenerationContext, variant: ReportType) -> ReportSection:
    """Recording quality as measured by ECG ingestion, not by reporting.

    These are the ingestion preprocessing outputs that already exist. The
    Signal Processing quality *metrics* are a separate, still-unavailable
    section (Sprint 2.10).
    """
    quality = context.ecg.quality
    values = [
        value_of("Quality score", _number(quality.quality_score, decimals=2)),
        value_of("Accepted beats", _number(quality.beat_count)),
        value_of("Validation status", _text(quality.validation_status)),
    ]
    if variant is ReportType.DETAILED:
        sp_quality = context.signal_processing.signal_quality_metrics
        values += [
            value_of("Quality flags", ", ".join(quality.quality_flags) if quality.quality_flags else None),
            value_of("Validation issues", _number(len(quality.validation_issues))),
            _sp_text("SP preprocessing status", sp_quality, "preprocessing_status"),
            _sp_text("QRS QC status", sp_quality, "qrs_qc_status"),
            _measurement("R-peak count", sp_quality, "r_peak_count"),
            _sp_text("Leads analyzed", sp_quality, "leads_analyzed"),
        ]
    return ReportSection(
        id=SectionId.SIGNAL_QUALITY,
        title="Signal Quality",
        values=tuple(values),
        notes=("Derived from ECG ingestion preprocessing.",),
    )


def build_visualization_section(
    context: GenerationContext,
    variant: ReportType,
    visualization: PendingReportArtifact | None,
    unavailable_reason: str | None = None,
) -> ReportSection:
    """The raw ECG rhythm strip, referenced from the artifact store (Sprint 4.19).

    Both variants show the same strip; when none could be drawn the section
    keeps its place and states why (Sprint 4.14 No Fabrication Policy).
    """
    if visualization is None:
        return ReportSection.unavailable(
            SectionId.RAW_ECG_VISUALIZATION,
            "Raw ECG",
            unavailable_reason or "No ECG visualization is available for this recording",
        )

    metadata = visualization.artifact_metadata
    lead = metadata.get("lead")
    values: tuple[ReportValue, ...] = ()
    if variant is ReportType.DETAILED:
        values = (
            value_of("Lead", lead),
            value_of("Window start", _number(metadata.get("window_start_second"), decimals=1), unit="s"),
            value_of("Window end", _number(metadata.get("window_end_second"), decimals=1), unit="s"),
            value_of("Sampling rate", _number(metadata.get("sampling_rate_hz")), unit="Hz"),
        )

    return ReportSection(
        id=SectionId.RAW_ECG_VISUALIZATION,
        title="Raw ECG",
        values=values,
        figures=(
            ReportFigure(
                caption=f"Raw ECG rhythm strip, lead {lead}" if lead else "Raw ECG rhythm strip",
                artifact_type=visualization.artifact_type,
                storage_location=visualization.storage_location,
                absolute_path=visualization.absolute_path,
                media_type=visualization.content_type,
                figure_metadata=metadata,
            ),
        ),
        notes=("Displayed at 25 mm/s and 10 mm/mV.",),
    )


def build_footer_section(context: GenerationContext, variant: ReportType) -> ReportSection:
    """Provenance shown on every page (Sprint 6.18).

    The report identifier and template version are added by the Template
    Engine, which is where they first exist.
    """
    generation = context.generation
    return ReportSection(
        id=SectionId.REPORT_FOOTER,
        title="Report Provenance",
        values=(
            value_of("ECG record", generation.ecg_record_id),
            value_of("Generation job", generation.job_id),
            value_of("Report version", str(generation.report_version)),
            value_of("Pipeline version", generation.pipeline_version),
            value_of("Schema version", generation.schema_version),
            value_of("Software version", generation.software_version),
            value_of("Generated", _moment(generation.generated_at)),
        ),
        notes=(
            "This report was generated automatically and is subject to clinician review.",
        ),
    )


def build_acquisition_metrics_section(context: GenerationContext) -> ReportSection:
    """The acquisition metric strip of the recording page."""
    ecg = context.ecg
    quality = ecg.quality
    beat_selection = context.signal_processing.beat_selection
    return ReportSection(
        id=SectionId.ACQUISITION_METRICS,
        title="Acquisition Metrics",
        values=(
            value_of("Duration", _duration(ecg.duration_seconds)),
            value_of("Sampling", _number(ecg.sampling_rate_hz), unit="Hz"),
            value_of("Accepted beats", _number(quality.beat_count)),
            _measurement(
                "QRS-SAECG rejected beats", beat_selection, "qrs_saecg_beats_rejected"
            ),
            unavailable_value("Noise floor", unit="µV RMS"),
        ),
    )


def build_recording_acceptance_section(context: GenerationContext) -> ReportSection:
    """Whether the recording was accepted for analysis, per ingestion validation."""
    quality = context.ecg.quality
    return ReportSection(
        id=SectionId.RECORDING_ACCEPTANCE,
        title="Recording Acceptance",
        values=(
            value_of("Validation status", _text(quality.validation_status)),
            value_of("Accepted beats", _number(quality.beat_count)),
            value_of("Quality score", _number(quality.quality_score, decimals=2)),
            unavailable_value("Acceptance grade"),
        ),
        notes=("Acceptance reflects ECG ingestion validation, not signal analysis.",),
    )


def build_lead_quality_section(context: GenerationContext) -> ReportSection:
    """One entry per recorded lead.

    Per-lead quality percentages come from Signal Processing; Phase 1 lists the
    leads that are present and marks their quality as awaited.
    """
    leads = context.ecg.available_leads
    if not leads:
        return ReportSection.unavailable(
            SectionId.LEAD_QUALITY, "Lead Quality Matrix", "No lead information is recorded"
        )
    return ReportSection(
        id=SectionId.LEAD_QUALITY,
        title="Lead Quality Matrix",
        values=tuple(unavailable_value(lead, "Per-lead quality is not produced by Signal Processing") for lead in leads),
    )


def build_recording_note_section(context: GenerationContext) -> ReportSection:
    """Ingestion validation findings shown alongside the recording."""
    issues = context.ecg.quality.validation_issues
    flags = context.ecg.quality.quality_flags
    notes: list[str] = []
    if flags:
        notes.append(f"Quality flags raised during ingestion: {', '.join(flags)}.")
    for issue in issues:
        message = issue.get("message") or issue.get("code")
        if message:
            notes.append(str(message))
    if not notes:
        notes.append("No ingestion validation issues were recorded for this recording.")
    return ReportSection(
        id=SectionId.RECORDING_NOTE, title="Recording Note", notes=tuple(notes)
    )


def build_traceability_chain_section(context: GenerationContext) -> ReportSection:
    """The end-to-end chain from source recording to generated report (Sprint 3.17)."""
    ecg = context.ecg
    generation = context.generation
    return ReportSection(
        id=SectionId.TRACEABILITY_CHAIN,
        title="End-to-End Traceability",
        values=(
            value_of("ECG source", _text(ecg.canonical_record_id) or ecg.ecg_record_id),
            value_of(
                "Ingestion",
                f"{ecg.lead_count} leads · {_number(ecg.sampling_rate_hz)} Hz"
                if ecg.lead_count and ecg.sampling_rate_hz
                else None,
            ),
            value_of("Preprocess", _text(ecg.quality.validation_status)),
            value_of(
                "Feature extraction",
                "Completed via app.signal_processing.analysis.analyze_waveform"
                if context.signal_processing.is_available
                else None,
            )
            if context.signal_processing.is_available
            else awaiting_signal_processing("Feature extraction"),
            unavailable_value("Rule evaluation", CLINICAL_RULES_NOT_CONFIGURED),
            value_of("Report", f"version {generation.report_version}"),
        ),
    )


def build_acquisition_record_section(context: GenerationContext) -> ReportSection:
    """The device and acquisition facts of the technical appendix."""
    ecg = context.ecg
    return ReportSection(
        id=SectionId.ACQUISITION_RECORD,
        title="Acquisition Record",
        values=(
            value_of("Recorder model", _text(ecg.device_source)),
            value_of("Source format", _text(ecg.source_format) or _text(ecg.file_type)),
            value_of("Lead configuration", _number(ecg.lead_count)),
            value_of("Sampling rate", _number(ecg.sampling_rate_hz), unit="Hz"),
            value_of("Amplitude units", _text(ecg.units)),
            value_of("Recording duration", _duration(ecg.duration_seconds)),
            value_of("Sample count", _number(ecg.sample_count)),
        ),
    )


def build_processing_record_section(context: GenerationContext) -> ReportSection:
    """What ingestion preprocessing produced for this recording."""
    quality = context.ecg.quality
    sp_quality = context.signal_processing.signal_quality_metrics
    beat_selection = context.signal_processing.beat_selection
    return ReportSection(
        id=SectionId.PROCESSING_RECORD,
        title="Signal and Processing Record",
        values=(
            value_of("Accepted beats", _number(quality.beat_count)),
            value_of("Quality score", _number(quality.quality_score, decimals=2)),
            value_of("Validation status", _text(quality.validation_status)),
            value_of("Validation issues", _number(len(quality.validation_issues))),
            value_of(
                "Quality flags",
                ", ".join(quality.quality_flags) if quality.quality_flags else None,
            ),
            _sp_text("SP preprocessing status", sp_quality, "preprocessing_status"),
            _sp_text("QRS QC status", sp_quality, "qrs_qc_status"),
            _measurement("R-peak count", sp_quality, "r_peak_count"),
            _sp_text("Leads analyzed", sp_quality, "leads_analyzed"),
            _measurement(
                "QRS-SAECG beats extracted", beat_selection, "qrs_saecg_beats_extracted"
            ),
            _measurement("QRS-SAECG beats used", beat_selection, "qrs_saecg_beats_used"),
            _measurement(
                "QRS-SAECG beats rejected", beat_selection, "qrs_saecg_beats_rejected"
            ),
            _measurement(
                "QRS-SAECG SNR", beat_selection, "qrs_saecg_snr_db", unit="dB", decimals=1
            ),
            _measurement("P-SAECG beats used", beat_selection, "p_saecg_beats_used"),
            _measurement(
                "P-SAECG SNR", beat_selection, "p_saecg_snr_db", unit="dB", decimals=1
            ),
            unavailable_value("Residual noise"),
        ),
    )


def build_software_record_section(context: GenerationContext) -> ReportSection:
    """The versioned software that produced this report (Sprint 3.18)."""
    generation = context.generation
    sp_quality = context.signal_processing.signal_quality_metrics
    ecg_parameters = context.signal_processing.ecg_parameters
    sp_executed = context.signal_processing.is_available
    return ReportSection(
        id=SectionId.SOFTWARE_RECORD,
        title="Software and Algorithm Record",
        values=(
            value_of("Reporting software", generation.software_version),
            value_of("Pipeline version", generation.pipeline_version),
            value_of("Schema version", generation.schema_version),
            value_of(
                "Signal processing",
                "app.signal_processing.analysis.analyze_waveform" if sp_executed else None,
            )
            if sp_executed
            else awaiting_signal_processing("Signal processing"),
            unavailable_value(
                "Beat detector",
                "Beat-detector method is not exposed by SignalProcessingResult",
            )
            if sp_executed
            else awaiting_signal_processing("Beat detector"),
            _sp_text("QRS delineation method", sp_quality, "qrs_delineation_method"),
            _sp_text("Reference lead", ecg_parameters, "reference_lead"),
            unavailable_value(
                "Decision limits",
                "Decision limits are not produced or configured by the existing system",
            ),
        ),
    )


def build_report_provenance_section(context: GenerationContext) -> ReportSection:
    """Report identity and review state.

    The report identifier and template version are added by the Template
    Engine, which is where they first exist.
    """
    generation = context.generation
    return ReportSection(
        id=SectionId.REPORT_PROVENANCE,
        title="Report Provenance",
        values=(
            value_of("Report generated", _moment(generation.generated_at)),
            value_of("Report version", str(generation.report_version)),
            value_of("Generation job", generation.job_id),
            value_of("Verification state", "Placeholder / inactive"),
            value_of("Electronic signature", "Not applied"),
        ),
    )


# ---------------------------------------------------------------------------
# Sections awaiting Signal Processing (Phase 1 placeholders)
# ---------------------------------------------------------------------------

#: The four parts of every clinical interpretation block in the specification.
INTERPRETATION_PARTS: tuple[str, ...] = (
    "Observation",
    "Evidence",
    "Clinical meaning",
    "Consideration",
)


def _awaiting_section(
    section_id: SectionId,
    title: str,
    labels: tuple[tuple[str, str | None], ...] = (),
) -> ReportSection:
    """A section whose every value awaits Signal Processing.

    The labels are kept so the approved layout renders its full structure with
    placeholders where the values will go (Sprint 6.16).
    """
    return ReportSection(
        id=section_id,
        title=title,
        availability=Availability.AWAITING_SIGNAL_PROCESSING,
        placeholder=PLACEHOLDER_AWAITING_SIGNAL_PROCESSING,
        values=tuple(awaiting_signal_processing(label, unit=unit) for label, unit in labels),
    )


def _unavailable_section(
    section_id: SectionId,
    title: str,
    reason: str,
    labels: tuple[tuple[str, str | None], ...] = (),
) -> ReportSection:
    """A section whose source was evaluated but did not produce the requested result."""
    return ReportSection(
        id=section_id,
        title=title,
        availability=Availability.NOT_AVAILABLE,
        placeholder=reason,
        values=tuple(unavailable_value(label, reason, unit=unit) for label, unit in labels),
    )


def _awaiting_interpretation(section_id: SectionId, title: str) -> ReportSection:
    """A four-part clinical interpretation block, awaiting analysis."""
    return _awaiting_section(section_id, title, tuple((part, None) for part in INTERPRETATION_PARTS))


def _measurement(
    label: str, section: ContextSection, key: str, *, unit: str | None = None, decimals: int = 0
) -> ReportValue:
    """One value sourced from a populated Signal Processing section (Sprint 5.7 Phase 2).

    Awaits, exactly as before, when Signal Processing has nothing at all for
    this recording (section not AVAILABLE -- e.g. the waveform could not be
    read); shows "not available" rather than awaiting when the section IS
    populated but this specific metric came back empty for this recording
    (e.g. too few beats for a stable SAECG average) -- that distinction is
    the ``Availability`` enum's own documented meaning.
    """
    if not section.is_available:
        return awaiting_signal_processing(label, unit=unit)
    payload = section.payload or {}
    value = _number(payload.get(key), decimals=decimals)
    if value is None:
        return unavailable_value(label, unit=unit)
    return value_of(label, value, unit=unit)


def _sp_text(label: str, section: ContextSection, key: str) -> ReportValue:
    """A non-numeric value copied verbatim from a populated SP context section."""
    if not section.is_available:
        return awaiting_signal_processing(label)
    value = (section.payload or {}).get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        return unavailable_value(label)
    if isinstance(value, (tuple, list)):
        value = ", ".join(str(item) for item in value)
    return value_of(label, str(value))


def build_rhythm_metrics_section(context: GenerationContext) -> ReportSection:
    """Key ECG parameters -- rate, rhythm and intervals (Sprint 5.4)."""
    ecg_parameters = context.signal_processing.ecg_parameters
    return ReportSection(
        id=SectionId.RHYTHM_METRICS,
        title="Rhythm & Intervals",
        values=(
            _measurement("Rate", ecg_parameters, "heart_rate_bpm", unit="bpm"),
            unavailable_value("Rhythm"),  # not computed by the authoritative SP result
            unavailable_value("PR", unit="ms"),
            _measurement("RR", ecg_parameters, "rr_interval_ms", unit="ms"),
            _measurement("QRS", ecg_parameters, "qrs_duration_median_ms", unit="ms"),
            _measurement("QTc", ecg_parameters, "qtc_bazett_ms", unit="ms"),
        ),
    )


def build_standard_ecg_measurements_section(context: GenerationContext) -> ReportSection:
    ecg_parameters = context.signal_processing.ecg_parameters
    return ReportSection(
        id=SectionId.STANDARD_ECG_MEASUREMENTS,
        title="Conventional Measurements",
        values=(
            _measurement("Heart rate", ecg_parameters, "heart_rate_bpm", unit="bpm"),
            unavailable_value("PR interval", unit="ms"),
            _measurement("RR interval", ecg_parameters, "rr_interval_ms", unit="ms"),
            _measurement("QRS duration", ecg_parameters, "qrs_duration_median_ms", unit="ms"),
            _measurement("QT interval", ecg_parameters, "qt_interval_ms", unit="ms"),
            _measurement("QTc", ecg_parameters, "qtc_bazett_ms", unit="ms"),
            unavailable_value("P axis", unit="°"),
            unavailable_value("QRS axis", unit="°"),
        ),
    )


def build_beat_visualization_section() -> ReportSection:
    return ReportSection.unavailable(
        SectionId.BEAT_VISUALIZATION, "Annotated Representative Beat", ANNOTATION_NOT_PRODUCED
    )


def build_atrial_visualization_section() -> ReportSection:
    return ReportSection.unavailable(
        SectionId.ATRIAL_VISUALIZATION, "Surface and Filtered P-wave Overlay", ANNOTATION_NOT_PRODUCED
    )


def build_atrial_criteria_section(context: GenerationContext) -> ReportSection:
    clinical_measurements = context.signal_processing.clinical_measurements
    return ReportSection(
        id=SectionId.ATRIAL_CRITERIA,
        title="ALP Evidence Ladder",
        values=(
            _measurement("Filtered P duration", clinical_measurements, "filtered_p_duration_ms", unit="ms"),
            _measurement("Terminal low-amplitude signal", clinical_measurements, "las20_ms", unit="ms"),
            _measurement("Inter-lead dispersion", clinical_measurements, "p_wave_dispersion_ms", unit="ms"),
        ),
    )


def build_atrial_measurements_section(context: GenerationContext) -> ReportSection:
    clinical_measurements = context.signal_processing.clinical_measurements
    return ReportSection(
        id=SectionId.ATRIAL_MEASUREMENTS,
        title="Atrial Measurements",
        values=(
            _measurement("P duration", clinical_measurements, "p_duration_ms", unit="ms"),
            _measurement("Filtered P", clinical_measurements, "filtered_p_duration_ms", unit="ms"),
            _measurement("P dispersion", clinical_measurements, "p_wave_dispersion_ms", unit="ms"),
            _measurement("LAS20", clinical_measurements, "las20_ms", unit="ms"),
            _measurement("RMS20", clinical_measurements, "rms20_uv", unit="µV", decimals=1),
            # Present/Absent classification needs the medical team's confirmed
            # RMS20/LAS20 thresholds -- see app/signal_processing/README.md.
            unavailable_value("ALP status", CLINICAL_RULES_NOT_CONFIGURED),
        ),
    )


def build_vlp_verdict_section() -> ReportSection:
    return _unavailable_section(
        SectionId.VLP_VERDICT,
        "Ventricular Late Potentials",
        CLINICAL_RULES_NOT_CONFIGURED,
        (("VLP classification", None),),
    )


def build_saecg_processing_section(context: GenerationContext) -> ReportSection:
    beat_selection = context.signal_processing.beat_selection
    return ReportSection(
        id=SectionId.SAECG_PROCESSING,
        title="SAECG Processing Chain",
        values=(
            _measurement("Accepted beats", beat_selection, "qrs_saecg_beats_used"),
            unavailable_value("Fiducial alignment"),
            unavailable_value("Signal average"),
            unavailable_value("Bidirectional filter"),
            unavailable_value("Terminal QRS"),
        ),
    )


def build_saecg_visualization_section() -> ReportSection:
    return ReportSection.unavailable(
        SectionId.SAECG_VISUALIZATION,
        "Filtered Signal-Averaged Terminal QRS",
        ANNOTATION_NOT_PRODUCED,
    )


def build_saecg_section(context: GenerationContext) -> ReportSection:
    clinical_measurements = context.signal_processing.clinical_measurements
    return ReportSection(
        id=SectionId.SAECG_PARAMETERS,
        title="Signal-Averaged ECG",
        values=(
            _measurement("Filtered QRS", clinical_measurements, "filtered_qrs_duration_ms", unit="ms"),
            _measurement("LAS40", clinical_measurements, "las40_ms", unit="ms"),
            _measurement("RMS40", clinical_measurements, "rms40_uv", unit="µV", decimals=1),
            # Present/Absent classification needs the medical team's confirmed
            # LAS40/RMS40 thresholds -- see app/signal_processing/README.md.
            unavailable_value("VLP classification", CLINICAL_RULES_NOT_CONFIGURED),
        ),
    )


def build_repolarization_timing_section(context: GenerationContext) -> ReportSection:
    ecg_parameters = context.signal_processing.ecg_parameters
    return ReportSection(
        id=SectionId.REPOLARIZATION_TIMING,
        title="Repolarization Timing",
        values=(
            _measurement("QTc", ecg_parameters, "qtc_bazett_ms", unit="ms"),
            _measurement("Tpeak-Tend", ecg_parameters, "tpe_ms", unit="ms"),
        ),
    )


def build_repolarization_visualization_section() -> ReportSection:
    return ReportSection.unavailable(
        SectionId.REPOLARIZATION_VISUALIZATION,
        "Annotated ST-T Recovery Interval",
        ANNOTATION_NOT_PRODUCED,
    )


def build_repolarization_section(context: GenerationContext) -> ReportSection:
    ecg_parameters = context.signal_processing.ecg_parameters
    return ReportSection(
        id=SectionId.REPOLARIZATION_ANALYSIS,
        title="Recovery Measurements",
        values=(
            _measurement("QT", ecg_parameters, "qt_interval_ms", unit="ms"),
            _measurement("QTc", ecg_parameters, "qtc_bazett_ms", unit="ms"),
            _measurement("Tpeak-Tend", ecg_parameters, "tpe_ms", unit="ms"),
            _measurement("QT dispersion", ecg_parameters, "qt_dispersion_global_ms", unit="ms"),
            _measurement("T-wave dispersion", ecg_parameters, "t_wave_dispersion_ms", unit="ms"),
        ),
    )


def build_domain_evidence_section() -> ReportSection:
    """The page-one ledger of one row per clinical domain."""
    return _unavailable_section(
        SectionId.DOMAIN_EVIDENCE_SUMMARY,
        "Domain Evidence Summary",
        CLINICAL_RULES_NOT_CONFIGURED,
        (
            ("Recording integrity", None),
            ("Standard ECG", None),
            ("Atrial conduction", None),
            ("Ventricular SAECG", None),
            ("Repolarization", None),
        ),
    )


def build_confidence_section(context: GenerationContext) -> ReportSection:
    """Signal quality, analysis confidence and study acceptance."""
    quality = context.ecg.quality
    return ReportSection(
        id=SectionId.CONFIDENCE_SUMMARY,
        title="Confidence and Acceptance",
        values=(
            value_of("Signal quality", _number(quality.quality_score, decimals=2)),
            unavailable_value("Analysis confidence", CLINICAL_RULES_NOT_CONFIGURED),
            value_of("Study acceptance", _text(quality.validation_status)),
        ),
    )


def build_evidence_ledger_section() -> ReportSection:
    return _unavailable_section(
        SectionId.EVIDENCE_LEDGER,
        "Supporting Evidence Ledger",
        CLINICAL_RULES_NOT_CONFIGURED,
        (("Atrial conduction", None), ("Ventricular SAECG", None), ("Repolarization", None)),
    )


def build_clinical_review_section() -> ReportSection:
    """The clinician review checkpoints, pending until a clinician completes them."""
    checkpoints = (
        "Symptom-rhythm concordance",
        "Structural context",
        "Longitudinal comparison",
    )
    return ReportSection(
        id=SectionId.CLINICAL_REVIEW,
        title="Clinical Review Documentation",
        values=tuple(
            ReportValue(
                label=label,
                availability=Availability.NOT_AVAILABLE,
                placeholder="Clinician note · pending",
            )
            for label in checkpoints
        ),
    )


def build_method_provenance_section(context: GenerationContext) -> ReportSection:
    sp_quality = context.signal_processing.signal_quality_metrics
    ecg_parameters = context.signal_processing.ecg_parameters
    return ReportSection(
        id=SectionId.METHOD_PROVENANCE,
        title="Measurement and Rule Provenance",
        values=(
            value_of(
                "Signal-processing entry point",
                "app.signal_processing.analysis.analyze_waveform"
                if context.signal_processing.is_available
                else None,
            )
            if context.signal_processing.is_available
            else awaiting_signal_processing("Signal-processing entry point"),
            _sp_text("Reference lead", ecg_parameters, "reference_lead"),
            _sp_text("QRS delineation method", sp_quality, "qrs_delineation_method"),
            unavailable_value(
                "Clinical decision limits",
                "Decision limits are not produced or configured by the existing system",
            ),
        ),
    )


def build_page_takeaways_section() -> ReportSection:
    """The per-page clinician takeaway, produced by the narrative engine."""
    return _unavailable_section(
        SectionId.PAGE_TAKEAWAYS,
        "Doctor Takeaway",
        "Clinical narrative is not produced by the existing system",
        (
            ("Executive Clinical Summary", None),
            ("Recording & Signal Integrity", None),
            ("Standard ECG Assessment", None),
            ("Atrial Electrophysiology", None),
            ("Ventricular Electrophysiology", None),
            ("Repolarization Analysis", None),
            ("Integrated Clinical Assessment", None),
            ("Technical Appendix", None),
        ),
    )


def build_clinical_measurements_section(context: GenerationContext) -> ReportSection:
    ecg_parameters = context.signal_processing.ecg_parameters
    clinical = context.signal_processing.clinical_measurements
    return ReportSection(
        id=SectionId.CLINICAL_MEASUREMENTS,
        title="Clinical Measurements",
        values=(
            _measurement("Heart rate", ecg_parameters, "heart_rate_bpm", unit="bpm"),
            _measurement("RR", ecg_parameters, "rr_interval_ms", unit="ms"),
            _measurement("QRS", ecg_parameters, "qrs_duration_median_ms", unit="ms"),
            _measurement("QT", ecg_parameters, "qt_interval_ms", unit="ms"),
            _measurement("QTc Bazett", ecg_parameters, "qtc_bazett_ms", unit="ms"),
            _measurement("QTc Fridericia", ecg_parameters, "qtc_fridericia_ms", unit="ms"),
            _measurement("Tpeak-Tend", ecg_parameters, "tpe_ms", unit="ms"),
            _measurement("QT dispersion", ecg_parameters, "qt_dispersion_global_ms", unit="ms"),
            _measurement("T-wave dispersion", ecg_parameters, "t_wave_dispersion_ms", unit="ms"),
            _measurement("P duration", clinical, "p_duration_ms", unit="ms"),
            _measurement("Filtered P", clinical, "filtered_p_duration_ms", unit="ms"),
            _measurement("P dispersion", clinical, "p_wave_dispersion_ms", unit="ms"),
            _measurement("LAS20", clinical, "las20_ms", unit="ms"),
            _measurement("RMS20", clinical, "rms20_uv", unit="µV", decimals=1),
            _measurement("Filtered QRS", clinical, "filtered_qrs_duration_ms", unit="ms"),
            _measurement("LAS40", clinical, "las40_ms", unit="ms"),
            _measurement("RMS40", clinical, "rms40_uv", unit="µV", decimals=1),
        ),
    )


def build_clinical_flags_section() -> ReportSection:
    return ReportSection.unavailable(
        SectionId.CLINICAL_FLAGS, "Clinical Flags", CLINICAL_RULES_NOT_CONFIGURED
    )


def build_clinical_findings_section() -> ReportSection:
    return ReportSection.unavailable(
        SectionId.CLINICAL_FINDINGS, "Clinical Findings", CLINICAL_RULES_NOT_CONFIGURED
    )


def build_interpretation_section() -> ReportSection:
    """The executive integrated impression of page one."""
    return _unavailable_section(
        SectionId.INTERPRETATION,
        "Integrated Impression",
        CLINICAL_RULES_NOT_CONFIGURED,
        (("Integrated impression", None), ("Priority evidence", None)),
    )


def build_integrated_assessment_section() -> ReportSection:
    return _unavailable_section(
        SectionId.INTEGRATED_ASSESSMENT,
        "Overall Electrophysiological Impression",
        CLINICAL_RULES_NOT_CONFIGURED,
        (("Overall impression", None), ("Clinical correlation", None)),
    )


def build_recommendations_section() -> ReportSection:
    return ReportSection.unavailable(
        SectionId.RECOMMENDATIONS, "Recommendations", CLINICAL_RULES_NOT_CONFIGURED
    )


def build_standard_ecg_interpretation_section() -> ReportSection:
    return _unavailable_section(
        SectionId.STANDARD_ECG_INTERPRETATION,
        "Standard ECG Interpretation",
        CLINICAL_RULES_NOT_CONFIGURED,
        tuple((part, None) for part in INTERPRETATION_PARTS),
    )


def build_atrial_interpretation_section() -> ReportSection:
    return _unavailable_section(
        SectionId.ATRIAL_INTERPRETATION,
        "Atrial Interpretation",
        CLINICAL_RULES_NOT_CONFIGURED,
        tuple((part, None) for part in INTERPRETATION_PARTS),
    )


def build_ventricular_interpretation_section() -> ReportSection:
    return _unavailable_section(
        SectionId.VENTRICULAR_INTERPRETATION,
        "Ventricular Interpretation",
        CLINICAL_RULES_NOT_CONFIGURED,
        tuple((part, None) for part in INTERPRETATION_PARTS),
    )


def build_repolarization_interpretation_section() -> ReportSection:
    return _unavailable_section(
        SectionId.REPOLARIZATION_INTERPRETATION,
        "Repolarization Interpretation",
        CLINICAL_RULES_NOT_CONFIGURED,
        tuple((part, None) for part in INTERPRETATION_PARTS),
    )
