"""Device Metadata Extractor.

Purpose:
    Extract acquisition device information when available (Implementation
    Spec 12.10).

Input:
    ParsedECG

Output:
    DeviceMetadata
"""

from __future__ import annotations

from app.ecg.models.device_metadata import DeviceMetadata
from app.ingestion.metadata._coercion import first
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG


class DeviceMetadataExtractor:
    """Extracts DeviceMetadata from a ParsedECG's raw device info."""

    @staticmethod
    def extract(parsed: ParsedECG) -> DeviceMetadata:
        info = parsed.raw_device_info
        return DeviceMetadata(
            manufacturer=first(info, "manufacturer"),
            model=first(info, "model"),
            firmware_version=first(info, "firmware_version", "firmwareVersion"),
            serial_number=first(info, "serial_number", "serialNumber"),
            software_version=first(info, "software_version", "softwareVersion"),
        )
