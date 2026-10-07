"""Summary and Detailed report builders (Sprint 6.7 / 6.8).

Both builders read the same immutable Generation Context and the same section
builders, so the two variants can never disagree about a fact. They differ
only in which sections they include and how much of each they show
(Sprint 3.25).

Neither builder renders anything. They emit a ``ReportDocument`` of structured
sections; turning that into HTML is the Template Engine's sole responsibility
(Sprint 6.15 / 6.17).

Section order is fixed and identical across report versions (Sprint 6.10), so
a reader of version 3 finds the same information in the same place as in
version 1.
"""

from __future__ import annotations

from app.reporting.builders import section_builders as sb
from app.reporting.builders.sections import (
    ReportDocument,
    ReportDocumentMetadata,
    ReportSection,
    ReportType,
)
from app.reporting.context.generation_context import GenerationContext
from app.reporting.models.pending_artifact import PendingReportArtifact


def _metadata(context: GenerationContext) -> ReportDocumentMetadata:
    generation = context.generation
    return ReportDocumentMetadata(
        ecg_record_id=generation.ecg_record_id,
        job_id=generation.job_id,
        report_version=generation.report_version,
        generated_at=generation.generated_at,
        pipeline_version=generation.pipeline_version,
        schema_version=generation.schema_version,
        software_version=generation.software_version,
    )


class SummaryReportBuilder:
    """Builds the concise report a clinician reads first (Sprint 6.7).

    Contents: patient and clinician identity, the recording, its quality, the
    ECG strip, key parameters, clinical flags and a summary interpretation.
    Deep parameter tables and per-domain analyses belong to the Detailed
    report.
    """

    report_type = ReportType.SUMMARY

    def build(
        self,
        context: GenerationContext,
        *,
        visualization: PendingReportArtifact | None = None,
        visualization_unavailable_reason: str | None = None,
    ) -> ReportDocument:
        sections: tuple[ReportSection, ...] = (
            sb.build_header_section(context, self.report_type),
            sb.build_patient_section(context, self.report_type),
            sb.build_doctor_section(context, self.report_type),
            sb.build_recording_section(context, self.report_type),
            sb.build_signal_quality_section(context, self.report_type),
            sb.build_visualization_section(
                context, self.report_type, visualization, visualization_unavailable_reason
            ),
            sb.build_rhythm_metrics_section(context),
            sb.build_clinical_flags_section(),
            sb.build_interpretation_section(),
            sb.build_recommendations_section(),
            sb.build_footer_section(context, self.report_type),
        )
        return ReportDocument(
            report_type=self.report_type,
            title="Clinical Summary Report",
            metadata=_metadata(context),
            sections=sections,
        )


class DetailedReportBuilder:
    """Builds the comprehensive report (Sprint 6.8).

    Sections are emitted in the order of the canonical Detailed Report
    specification, grouped by the page each appears on, so the Template Engine
    binds them into the approved layout without reordering anything.
    """

    report_type = ReportType.DETAILED

    def build(
        self,
        context: GenerationContext,
        *,
        visualization: PendingReportArtifact | None = None,
        visualization_unavailable_reason: str | None = None,
    ) -> ReportDocument:
        sections: tuple[ReportSection, ...] = (
            # Page 1 -- Executive Clinical Summary
            sb.build_header_section(context, self.report_type),
            sb.build_patient_section(context, self.report_type),
            sb.build_doctor_section(context, self.report_type),
            sb.build_interpretation_section(),
            sb.build_domain_evidence_section(),
            sb.build_confidence_section(context),
            # Page 2 -- Recording & Signal Integrity
            sb.build_recording_acceptance_section(context),
            sb.build_acquisition_metrics_section(context),
            sb.build_recording_section(context, self.report_type),
            sb.build_visualization_section(
                context, self.report_type, visualization, visualization_unavailable_reason
            ),
            sb.build_lead_quality_section(context),
            sb.build_recording_note_section(context),
            sb.build_signal_quality_section(context, self.report_type),
            # Page 3 -- Standard ECG Assessment
            sb.build_rhythm_metrics_section(context),
            sb.build_standard_ecg_measurements_section(context),
            sb.build_beat_visualization_section(),
            sb.build_standard_ecg_interpretation_section(),
            # Page 4 -- Atrial Electrophysiology
            sb.build_atrial_visualization_section(),
            sb.build_atrial_criteria_section(context),
            sb.build_atrial_measurements_section(context),
            sb.build_atrial_interpretation_section(),
            # Page 5 -- Ventricular Electrophysiology
            sb.build_vlp_verdict_section(),
            sb.build_saecg_processing_section(context),
            sb.build_saecg_visualization_section(),
            sb.build_saecg_section(context),
            sb.build_ventricular_interpretation_section(),
            # Page 6 -- Repolarization Analysis
            sb.build_repolarization_timing_section(context),
            sb.build_repolarization_visualization_section(),
            sb.build_repolarization_section(context),
            sb.build_repolarization_interpretation_section(),
            # Page 7 -- Integrated Clinical Assessment
            sb.build_integrated_assessment_section(),
            sb.build_evidence_ledger_section(),
            sb.build_clinical_findings_section(),
            sb.build_clinical_measurements_section(context),
            sb.build_clinical_flags_section(),
            sb.build_recommendations_section(),
            sb.build_clinical_review_section(),
            # Page 8 -- Technical Appendix
            sb.build_traceability_chain_section(context),
            sb.build_acquisition_record_section(context),
            sb.build_processing_record_section(context),
            sb.build_software_record_section(context),
            sb.build_report_provenance_section(context),
            sb.build_method_provenance_section(context),
            # Every page
            sb.build_page_takeaways_section(),
            sb.build_footer_section(context, self.report_type),
        )
        return ReportDocument(
            report_type=self.report_type,
            title="Clinical Diagnostic Report",
            metadata=_metadata(context),
            sections=sections,
        )
