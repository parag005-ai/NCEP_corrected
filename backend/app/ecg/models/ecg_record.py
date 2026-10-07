"""ECGRecord: the canonical internal representation of an ECG recording.

ECGRecord is the only normalized ECG object exchanged between ingestion,
validation, preprocessing, analysis, reporting, storage, and background
tasks (ECGRecord.md, Implementation Spec Chapter 13.6). It is created
exclusively by the ECGRecord Builder and, once constructed, is never
modified by the ingestion subsystem (Builder Design Principle 13.15).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ecg.models.annotations import Annotations
from app.ecg.models.clinical_metadata import ClinicalMetadata
from app.ecg.models.device_metadata import DeviceMetadata
from app.ecg.models.ecg_metadata import ECGMetadata
from app.ecg.models.patient_metadata import PatientMetadata
from app.ecg.models.quality_metadata import QualityMetadata
from app.ecg.models.source_information import SourceInformation
from app.ecg.models.waveform import Waveform


@dataclass(frozen=True)
class ECGRecord:
    """The unified internal representation of one uploaded ECG recording.

    Exactly one ECGRecord exists per uploaded recording (Business Rule
    8.3). No parser-specific structures (XML tags, DICOM elements, SCP
    sections, WFDB constructs) may appear anywhere within it.
    """

    record_id: str
    waveform: Waveform
    patient_metadata: PatientMetadata
    ecg_metadata: ECGMetadata
    clinical_metadata: ClinicalMetadata
    device_metadata: DeviceMetadata
    quality_metadata: QualityMetadata
    annotations: Annotations
    source_information: SourceInformation
