"""Internal ECG domain model package.

Exposes the canonical NCEP domain objects. Downstream modules should import
from here rather than reaching into individual submodules.
"""

from app.ecg.models.annotations import Annotation, AnnotationType, Annotations
from app.ecg.models.clinical_metadata import ClinicalMetadata
from app.ecg.models.device_metadata import DeviceMetadata
from app.ecg.models.ecg_metadata import ECGMetadata
from app.ecg.models.ecg_record import ECGRecord
from app.ecg.models.patient_metadata import PatientMetadata
from app.ecg.models.quality_metadata import QualityMetadata
from app.ecg.models.source_information import SourceInformation
from app.ecg.models.waveform import LeadSignal, Waveform

__all__ = [
    "Annotation",
    "AnnotationType",
    "Annotations",
    "ClinicalMetadata",
    "DeviceMetadata",
    "ECGMetadata",
    "ECGRecord",
    "LeadSignal",
    "PatientMetadata",
    "QualityMetadata",
    "SourceInformation",
    "Waveform",
]
