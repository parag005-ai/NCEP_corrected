"""Metadata Orchestrator.

Purpose:
    Coordinate all metadata extraction for one ParsedECG (Implementation
    Spec 12.6).

Responsibilities:
    - Invoke all five metadata extractors (patient, ecg, clinical, device,
      quality).
    - Aggregate their outputs into one ExtractedMetadata bundle.

Shall NOT:
    - Perform validation.
    - Modify the waveform.
    - Store data.
    - Generate missing metadata.

Input:
    ParsedECG, the record identifier assigned to this ingestion.

Output:
    ExtractedMetadata (PatientMetadata, ECGMetadata, ClinicalMetadata,
    DeviceMetadata, QualityMetadata)
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ecg.models.clinical_metadata import ClinicalMetadata
from app.ecg.models.device_metadata import DeviceMetadata
from app.ecg.models.ecg_metadata import ECGMetadata
from app.ecg.models.patient_metadata import PatientMetadata
from app.ecg.models.quality_metadata import QualityMetadata
from app.ingestion.metadata.clinical.extractor import ClinicalMetadataExtractor
from app.ingestion.metadata.device.extractor import DeviceMetadataExtractor
from app.ingestion.metadata.ecg.extractor import ECGMetadataExtractor
from app.ingestion.metadata.patient.extractor import PatientMetadataExtractor
from app.ingestion.metadata.quality.extractor import QualityMetadataExtractor
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG


@dataclass(frozen=True)
class ExtractedMetadata:
    """Aggregated output of the Metadata Framework for one ParsedECG."""

    patient: PatientMetadata
    ecg: ECGMetadata
    clinical: ClinicalMetadata
    device: DeviceMetadata
    quality: QualityMetadata


class MetadataOrchestrator:
    """Coordinates the five independent metadata extractors."""

    @staticmethod
    def extract(parsed: ParsedECG, record_id: str) -> ExtractedMetadata:
        return ExtractedMetadata(
            patient=PatientMetadataExtractor.extract(parsed),
            ecg=ECGMetadataExtractor.extract(parsed, record_id),
            clinical=ClinicalMetadataExtractor.extract(parsed),
            device=DeviceMetadataExtractor.extract(parsed),
            quality=QualityMetadataExtractor.extract(parsed),
        )
