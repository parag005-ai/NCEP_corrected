"""ECG Metadata Extractor.

Purpose:
    Extract recording-specific metadata from a ParsedECG (Implementation
    Spec 12.8).

Responsibilities:
    - Derive mandatory fields (sampling rate, lead count, duration, sample
      count, units) directly from the already-standardized Waveform.
    - Read optional acquisition fields from ParsedECG.raw_recording_info.

Shall NOT:
    - Validate the extracted metadata.
    - Modify the waveform.

Input:
    ParsedECG, the record identifier assigned to this ingestion.

Output:
    ECGMetadata
"""

from __future__ import annotations

from app.ecg.models.ecg_metadata import ECGMetadata
from app.ingestion.metadata._coercion import first, parse_datetime, parse_float
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG


class ECGMetadataExtractor:
    """Extracts ECGMetadata from a ParsedECG's waveform and raw recording info."""

    @staticmethod
    def extract(parsed: ParsedECG, record_id: str) -> ECGMetadata:
        waveform = parsed.waveform
        recording_info = parsed.raw_recording_info
        device_info = parsed.raw_device_info

        return ECGMetadata(
            record_id=record_id,
            source_format=parsed.source_format,
            sampling_rate_hz=waveform.sampling_rate_hz,
            lead_count=waveform.lead_count,
            available_leads=waveform.available_leads,
            xyz_available=waveform.xyz_available,
            recording_duration_seconds=waveform.duration_seconds,
            sample_count=waveform.sample_count,
            units=waveform.units,
            device_manufacturer=first(device_info, "manufacturer"),
            device_model=first(device_info, "model"),
            gain=parse_float(first(recording_info, "gain")),
            baseline=parse_float(first(recording_info, "baseline")),
            filter_settings=first(recording_info, "filter_settings", "filterSettings"),
            acquisition_timestamp=parse_datetime(
                first(recording_info, "acquisition_timestamp", "acquisitionTimestamp", "study_date")
            ),
            checksum=first(recording_info, "checksum"),
            recording_location=first(recording_info, "recording_location", "recordingLocation"),
            session_id=first(recording_info, "session_id", "sessionId"),
        )
