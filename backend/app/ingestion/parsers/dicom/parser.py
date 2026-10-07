"""DICOM Parser.

Purpose:
    Interprets a DICOM ECG Waveform Storage object (e.g. SOP Class
    "12-lead ECG Waveform Storage", 1.2.840.10008.5.1.4.1.1.9.1.1), extracts
    waveform and metadata, and constructs a ParsedECG (Implementation Spec
    10.11).

Responsibilities:
    - Read the DICOM Waveform Sequence (5400,0100) and decode channel
      samples using each channel's sensitivity/baseline/correction factor.
    - Map ChannelSourceSequence code meanings to canonical NCEP leads.
    - Extract patient, device, and study-level metadata via standard DICOM
      tags.
    - Build ParsedECG.

Shall NOT:
    - Validate the ECG.
    - Filter the signal.
    - Expose pydicom Dataset objects or DICOM tags beyond this module.

Input:
    A single uploaded DICOM file containing a Waveform Sequence.

Output:
    ParsedECG

Exceptions:
    MissingRequiredFileError, MalformedFileError, UnmappableLeadError
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pydicom

from app.ecg.constants import DEFAULT_SIGNAL_UNITS, ECGFormat, CanonicalLead
from app.ecg.lead_mapping import resolve_canonical_lead
from app.ecg.models.waveform import LeadSignal, Waveform
from app.ingestion.exceptions import MalformedFileError, MissingRequiredFileError
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.interfaces.parser import ParserInterface


def _optional_str(dataset, tag: str) -> str | None:
    value = getattr(dataset, tag, None)
    text = str(value).strip() if value is not None else ""
    return text or None


def _combine_dicom_datetime(date_str: str | None, time_str: str | None) -> str | None:
    """Combines a DICOM DA (date) value with an optional TM (time) value.

    DICOM frequently stores the acquisition date and time as two separate
    elements, and the time element is itself optional (a date-only
    recording is a valid DICOM object). Returning just the date when no
    time is present -- rather than requiring one -- lets the generic
    metadata coercion layer's date-only fallback still capture the date
    (Business Rule: never drop a value that was actually present in the
    source, and never fabricate one that was not).
    """
    if not date_str:
        return None
    date_str = date_str[:8]
    if not time_str:
        return date_str
    # TM value may be HH, HHMM, HHMMSS, or HHMMSS.FFFFFF -- normalize to HHMMSS.
    time_digits = time_str.split(".", 1)[0].ljust(6, "0")[:6]
    return f"{date_str}{time_digits}"


class DICOMParser(ParserInterface):
    """Parses DICOM ECG Waveform Storage objects into ParsedECG."""

    format = ECGFormat.DICOM

    def can_parse(self, files: Sequence[Path]) -> bool:
        return any(
            Path(f).suffix.lower() in {".dcm", ".dicom"} or self._looks_like_dicom(Path(f)) for f in files
        )

    def parse(self, files: Sequence[Path]) -> ParsedECG:
        file_list = [Path(f) for f in files]
        dicom_files = [
            f for f in file_list if f.suffix.lower() in {".dcm", ".dicom"} or self._looks_like_dicom(f)
        ]

        if not dicom_files:
            raise MissingRequiredFileError("DICOM parsing requires at least one .dcm file.")
        if len(dicom_files) > 1:
            raise MalformedFileError(
                "Multiple DICOM files were provided; one DICOM upload must represent exactly one recording."
            )
        dicom_file = dicom_files[0]

        try:
            dataset = pydicom.dcmread(str(dicom_file))
        except Exception as exc:
            raise MalformedFileError(f"Failed to read DICOM file {dicom_file.name}: {exc}") from exc

        if "WaveformSequence" not in dataset or not dataset.WaveformSequence:
            raise MalformedFileError(
                f"DICOM file {dicom_file.name} contains no WaveformSequence (not an ECG waveform object)."
            )

        waveform_item = dataset.WaveformSequence[0]
        waveform = self._build_waveform(waveform_item, dicom_file)

        raw_patient_info = {
            "patient_id": _optional_str(dataset, "PatientID"),
            "name": _optional_str(dataset, "PatientName"),
            "date_of_birth": _optional_str(dataset, "PatientBirthDate"),
            "sex": _optional_str(dataset, "PatientSex"),
            "age": _optional_str(dataset, "PatientAge"),
        }
        raw_patient_info = {k: v for k, v in raw_patient_info.items() if v}

        raw_device_info = {
            "manufacturer": _optional_str(dataset, "Manufacturer"),
            "model": _optional_str(dataset, "ManufacturerModelName"),
            "serial_number": _optional_str(dataset, "DeviceSerialNumber"),
            "software_version": _optional_str(dataset, "SoftwareVersions"),
        }
        raw_device_info = {k: v for k, v in raw_device_info.items() if v}

        acquisition_datetime = _optional_str(dataset, "AcquisitionDateTime")
        if acquisition_datetime:
            # DT value: YYYYMMDDHHMMSS.FFFFFF&ZZXX -- take the date+time prefix only.
            acquisition_timestamp = acquisition_datetime[:14]
        else:
            acquisition_timestamp = _combine_dicom_datetime(
                _optional_str(dataset, "AcquisitionDate") or _optional_str(dataset, "StudyDate"),
                _optional_str(dataset, "AcquisitionTime") or _optional_str(dataset, "StudyTime"),
            )

        raw_recording_info = {
            "record_id": _optional_str(dataset, "SOPInstanceUID"),
            "study_date": _optional_str(dataset, "StudyDate"),
            "study_time": _optional_str(dataset, "StudyTime"),
            "acquisition_timestamp": acquisition_timestamp,
        }
        raw_recording_info = {k: v for k, v in raw_recording_info.items() if v}

        raw_clinical_info = {}
        reason = _optional_str(dataset, "StudyDescription")
        if reason:
            raw_clinical_info["reason_for_examination"] = reason

        return ParsedECG(
            source_format=ECGFormat.DICOM,
            source_files=tuple(file_list),
            parser_name="DICOMParser",
            waveform=waveform,
            raw_patient_info=raw_patient_info,
            raw_recording_info=raw_recording_info,
            raw_clinical_info=raw_clinical_info,
            raw_device_info=raw_device_info,
            raw_quality_info={},
            raw_annotations=(),
        )

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _looks_like_dicom(path: Path) -> bool:
        try:
            with path.open("rb") as fh:
                fh.seek(128)
                return fh.read(4) == b"DICM"
        except OSError:
            return False

    @classmethod
    def _build_waveform(cls, waveform_item, dicom_file: Path) -> Waveform:
        try:
            sampling_rate_hz = float(waveform_item.SamplingFrequency)
            n_channels = int(waveform_item.NumberOfWaveformChannels)
            n_samples = int(waveform_item.NumberOfWaveformSamples)
        except AttributeError as exc:
            raise MalformedFileError(f"DICOM waveform item in {dicom_file.name} is missing required attributes: {exc}") from exc

        bits_allocated = int(getattr(waveform_item, "WaveformBitsAllocated", 16))
        dtype = np.int16 if bits_allocated == 16 else np.int32
        raw = np.frombuffer(waveform_item.WaveformData, dtype=dtype)
        try:
            raw = raw.reshape(n_samples, n_channels)
        except ValueError as exc:
            raise MalformedFileError(f"WaveformData size mismatch in {dicom_file.name}: {exc}") from exc

        channel_defs = getattr(waveform_item, "ChannelDefinitionSequence", None)
        if not channel_defs:
            raise MalformedFileError(f"DICOM waveform item in {dicom_file.name} has no ChannelDefinitionSequence.")

        leads: dict[CanonicalLead, LeadSignal] = {}
        units = DEFAULT_SIGNAL_UNITS
        for idx, channel in enumerate(channel_defs):
            lead_name = cls._channel_lead_name(channel, idx, dicom_file)
            canonical = resolve_canonical_lead(lead_name)
            if canonical in leads:
                raise MalformedFileError(f"Duplicate canonical lead {canonical.value} in {dicom_file.name}.")

            sensitivity = float(getattr(channel, "ChannelSensitivity", None) or 1.0)
            correction_factor = float(getattr(channel, "ChannelSensitivityCorrectionFactor", None) or 1.0)
            baseline = float(getattr(channel, "ChannelBaseline", None) or 0.0)
            physical = (raw[:, idx].astype(np.float64) - baseline) * sensitivity * correction_factor
            leads[canonical] = LeadSignal(canonical, physical)

            unit_seq = getattr(channel, "ChannelSensitivityUnitsSequence", None)
            if unit_seq:
                code_value = getattr(unit_seq[0], "CodeValue", None)
                if code_value:
                    units = str(code_value)

        return Waveform(leads=leads, sampling_rate_hz=sampling_rate_hz, units=units)

    @staticmethod
    def _channel_lead_name(channel, idx: int, dicom_file: Path) -> str:
        source_seq = getattr(channel, "ChannelSourceSequence", None)
        if source_seq:
            code_meaning = getattr(source_seq[0], "CodeMeaning", None)
            if code_meaning:
                return str(code_meaning)
        raise MalformedFileError(
            f"DICOM waveform channel {idx} in {dicom_file.name} has no ChannelSourceSequence lead identifier."
        )
