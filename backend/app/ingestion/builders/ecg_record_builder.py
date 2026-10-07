"""ECGRecord Builder.

Purpose:
    Assemble validated ingestion artifacts into the canonical ECGRecord --
    the single authoritative representation of an ECG recording throughout
    NCEP (Implementation Spec Chapter 13).

Responsibilities:
    - Accept only a ValidatedParsedECG (never a raw ParsedECG).
    - Assemble Waveform, PatientMetadata, ECGMetadata, ClinicalMetadata,
      DeviceMetadata, QualityMetadata, and Annotations into one ECGRecord.
    - Attach SourceInformation for lineage traceability (Business Rule
      8.17).

Shall NOT:
    - Parse files.
    - Validate data.
    - Modify waveform samples.
    - Perform preprocessing.
    - Generate clinical information.

Input:
    ValidatedParsedECG, the upload identifier for this ingestion.

Output:
    ECGRecord (immutable)

Exceptions:
    BuilderError -- raised if given input that has not passed validation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.ecg.models.annotations import Annotations
from app.ecg.models.ecg_record import ECGRecord
from app.ecg.models.source_information import SourceInformation
from app.ingestion.exceptions import BuilderError
from app.ingestion.validation.validation_result import ValidatedParsedECG


class ECGRecordBuilder:
    """Assembles a ValidatedParsedECG into the canonical, immutable ECGRecord."""

    @staticmethod
    def build(validated: ValidatedParsedECG, upload_id: str) -> ECGRecord:
        if not validated.validation_result.is_valid:
            raise BuilderError("Cannot build an ECGRecord from a ValidatedParsedECG that failed validation.")

        parsed = validated.parsed
        metadata = validated.metadata

        source_information = SourceInformation(
            upload_id=upload_id,
            source_format=parsed.source_format,
            original_filenames=tuple(f.name for f in parsed.source_files),
            parser_name=parsed.parser_name,
            ingested_at=datetime.now(timezone.utc),
        )

        return ECGRecord(
            record_id=metadata.ecg.record_id,
            waveform=parsed.waveform,
            patient_metadata=metadata.patient,
            ecg_metadata=metadata.ecg,
            clinical_metadata=metadata.clinical,
            device_metadata=metadata.device,
            quality_metadata=metadata.quality,
            annotations=Annotations(items=parsed.raw_annotations),
            source_information=source_information,
        )
