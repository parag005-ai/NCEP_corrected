"""Patient Metadata Extractor.

Purpose:
    Extract patient-related information from a ParsedECG (Implementation
    Spec 12.7).

Responsibilities:
    - Read patient fields from ParsedECG.raw_patient_info.
    - Leave absent fields unset rather than fabricating them.

Shall NOT:
    - Validate the extracted metadata.
    - Modify the waveform.
    - Invent missing values.

Input:
    ParsedECG

Output:
    PatientMetadata
"""

from __future__ import annotations

from app.ecg.models.patient_metadata import PatientMetadata
from app.ingestion.metadata._coercion import first, parse_date, parse_int
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG


class PatientMetadataExtractor:
    """Extracts PatientMetadata from a ParsedECG's raw patient info."""

    @staticmethod
    def extract(parsed: ParsedECG) -> PatientMetadata:
        info = parsed.raw_patient_info

        name = first(info, "name", "patient_name")
        if not name:
            last_name = first(info, "last_name")
            first_name = first(info, "first_name")
            if last_name or first_name:
                name = " ".join(part for part in (first_name, last_name) if part)

        return PatientMetadata(
            patient_id=first(info, "patient_id", "patientid", "id"),
            name=name,
            date_of_birth=parse_date(first(info, "date_of_birth", "dob")),
            age=parse_int(first(info, "age")),
            sex=first(info, "sex", "gender"),
            hospital=first(info, "hospital"),
            clinician=first(info, "clinician", "physician", "referring_physician"),
            clinical_history=first(info, "clinical_history", "history"),
        )
