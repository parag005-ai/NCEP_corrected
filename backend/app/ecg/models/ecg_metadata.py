"""ECGMetadata domain object.

Describes how a recording was acquired, never who it belongs to
(Implementation Spec 4.6 / 5.6). ECGMetadata is mandatory for every valid
ECGRecord -- if it cannot be extracted, the recording fails validation
(Business Rule 8.7).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.ecg.constants import CanonicalLead, ECGFormat


@dataclass(frozen=True)
class ECGMetadata:
    """Recording-related (acquisition) metadata."""

    record_id: str
    source_format: ECGFormat
    sampling_rate_hz: float
    lead_count: int
    available_leads: tuple[CanonicalLead, ...]
    xyz_available: bool
    recording_duration_seconds: float
    sample_count: int
    units: str

    # Optional -- presence depends on the source format (Implementation Spec 5.6).
    device_manufacturer: str | None = None
    device_model: str | None = None
    gain: float | None = None
    baseline: float | None = None
    filter_settings: str | None = None
    acquisition_timestamp: datetime | None = None
    checksum: str | None = None
    recording_location: str | None = None
    session_id: str | None = None
