"""Clinical Metadata Extractor.

Purpose:
    Extract clinical information accompanying the recording, preserved
    exactly as provided with no interpretation (Implementation Spec 12.9).

Input:
    ParsedECG

Output:
    ClinicalMetadata
"""

from __future__ import annotations

from app.ecg.models.clinical_metadata import ClinicalMetadata
from app.ingestion.metadata._coercion import first
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG


class ClinicalMetadataExtractor:
    """Extracts ClinicalMetadata from a ParsedECG's raw clinical info."""

    @staticmethod
    def extract(parsed: ParsedECG) -> ClinicalMetadata:
        info = parsed.raw_clinical_info

        medications = info.get("medications") or ()
        if isinstance(medications, str):
            medications = (medications,)
        else:
            medications = tuple(str(m) for m in medications)

        return ClinicalMetadata(
            diagnosis=first(info, "diagnosis", "diagnose"),
            reason_for_examination=first(
                info, "reason_for_examination", "reasonForExamination", "reason for admission"
            ),
            medications=medications,
            procedure_notes=first(info, "procedure_notes", "procedureNotes"),
            clinical_comments=first(info, "clinical_comments", "clinicalComments", "comments"),
        )
