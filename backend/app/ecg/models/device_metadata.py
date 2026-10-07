"""DeviceMetadata domain object.

Preserves acquisition device information when available (Implementation
Spec 3.7 / 12.10). Distinct from ECGMetadata's `device_manufacturer` /
`device_model` shorthand fields -- this object carries the fuller device
record when the source format exposes one.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceMetadata:
    """Acquisition device information, preserved verbatim when available."""

    manufacturer: str | None = None
    model: str | None = None
    firmware_version: str | None = None
    serial_number: str | None = None
    software_version: str | None = None

    def is_empty(self) -> bool:
        return not any(
            (self.manufacturer, self.model, self.firmware_version, self.serial_number, self.software_version)
        )
