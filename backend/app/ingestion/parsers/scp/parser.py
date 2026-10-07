"""SCP-ECG Parser.

Purpose:
    Interprets an SCP-ECG (EN 1064 / ISO 11073-91064) recording, extracts
    waveform and metadata, and constructs a ParsedECG (Implementation Spec
    10.12).

Scope (Phase 1) -- read before extending:
    SCP-ECG is a section-based binary container. This parser fully
    implements the container structure (file header, Section Pointer
    table) and interprets:
      - Section 1 (Patient/recording tags): tags 0/1/2 (last name, first
        name, patient ID) are well-established across the standard and are
        decoded; every other tag is preserved verbatim as raw bytes
        (`tag_<n>`) rather than guessed, per Business Rule 8.6/"never
        fabricate metadata".
      - Section 3 (Lead definition): the core 12-lead identification codes
        (I, II, III, aVR, aVL, aVF, V1-V6). Codes outside that set (e.g.
        V7-V9, which fall outside the NCEP canonical model) raise
        UnmappableLeadError rather than being dropped silently.
      - Section 6 (Rhythm data): AVM/sample-interval header, difference
        order 0/1/2 (none / first-difference / second-difference), decoded
        via cumulative sum. Bimodal (Huffman) compressed rhythm data is
        **not** decoded -- this parser raises UnsupportedVersionError for
        it rather than risk a silently wrong decode.

    No SCP-ECG sample file was available during Phase 1 development (unlike
    WFDB, which has the PTB Diagnostic ECG Database as its reference
    dataset). This implementation follows the published EN 1064 section
    layout; it has not been round-tripped against a real vendor export and
    should be verified against one before production use.

Shall NOT:
    - Validate the ECG.
    - Filter the signal.
    - Expose SCP section numbers outside this module (10.12).
    - Attempt to decode Huffman-compressed rhythm data.

Input:
    A single uploaded SCP-ECG (.scp) file.

Output:
    ParsedECG

Exceptions:
    MissingRequiredFileError, MalformedFileError, UnsupportedVersionError,
    UnmappableLeadError
"""

from __future__ import annotations

import struct
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from app.ecg.constants import DEFAULT_SIGNAL_UNITS, ECGFormat, CanonicalLead
from app.ecg.models.waveform import LeadSignal, Waveform
from app.ingestion.exceptions import (
    MalformedFileError,
    MissingRequiredFileError,
    UnmappableLeadError,
    UnsupportedVersionError,
)
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.interfaces.parser import ParserInterface

_SECTION_HEADER_LEN = 16
_POINTER_ENTRY_LEN = 10
_SECTION1_PATIENT_TAGS = {0: "last_name", 1: "first_name", 2: "patient_id"}

# Core SCP-ECG lead identification codes (EN 1064 Annex). Codes not present
# here (e.g. 9/10/11 = V7/V8/V9) are intentionally unmapped -- they fall
# outside the 15-slot NCEP canonical lead model.
_SCP_LEAD_ID_TO_CANONICAL: dict[int, CanonicalLead] = {
    1: CanonicalLead.I,
    2: CanonicalLead.II,
    3: CanonicalLead.V1,
    4: CanonicalLead.V2,
    5: CanonicalLead.V3,
    6: CanonicalLead.V4,
    7: CanonicalLead.V5,
    8: CanonicalLead.V6,
    12: CanonicalLead.III,
    13: CanonicalLead.aVR,
    14: CanonicalLead.aVL,
    15: CanonicalLead.aVF,
}


class SCPParser(ParserInterface):
    """Parses SCP-ECG (EN 1064) recordings into ParsedECG."""

    format = ECGFormat.SCP_ECG

    def can_parse(self, files: Sequence[Path]) -> bool:
        return any(Path(f).suffix.lower() in {".scp", ".scp-ecg"} for f in files)

    def parse(self, files: Sequence[Path]) -> ParsedECG:
        file_list = [Path(f) for f in files]
        scp_files = [f for f in file_list if f.suffix.lower() in {".scp", ".scp-ecg"}]

        if not scp_files:
            raise MissingRequiredFileError("SCP-ECG parsing requires a .scp file.")
        if len(scp_files) > 1:
            raise MalformedFileError(
                "Multiple .scp files were provided; one SCP-ECG upload must represent exactly one recording."
            )
        scp_file = scp_files[0]

        try:
            data = scp_file.read_bytes()
        except OSError as exc:
            raise MissingRequiredFileError(f"Could not read SCP-ECG file {scp_file.name}: {exc}") from exc

        if len(data) < 6 + _SECTION_HEADER_LEN:
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} is too small to contain a valid header.")

        sections = self._read_section_pointers(data, scp_file)

        section1 = sections.get(1)
        raw_patient_info, raw_recording_info_tags = self._parse_section1(data, section1) if section1 else ({}, {})

        section3 = sections.get(3)
        if section3 is None:
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} has no Section 3 (lead definition).")
        lead_order = self._parse_section3(data, section3, scp_file)

        section6 = sections.get(6)
        if section6 is None:
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} has no Section 6 (rhythm data).")
        waveform = self._parse_section6(data, section6, lead_order, scp_file)

        raw_recording_info = {"sections_present": sorted(sections.keys()), **raw_recording_info_tags}

        return ParsedECG(
            source_format=ECGFormat.SCP_ECG,
            source_files=tuple(file_list),
            parser_name="SCPParser",
            waveform=waveform,
            raw_patient_info=raw_patient_info,
            raw_recording_info=raw_recording_info,
            raw_clinical_info={},
            raw_device_info={},
            raw_quality_info={},
            raw_annotations=(),
        )

    # -- container structure -------------------------------------------------

    @staticmethod
    def _read_section_pointers(data: bytes, scp_file: Path) -> dict[int, tuple[int, int]]:
        """Returns {section_id: (start_offset, length)} using the Section 0 pointer table."""
        header_start = 6
        if len(data) < header_start + _SECTION_HEADER_LEN:
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} is missing Section 0.")

        section_id = struct.unpack_from("<H", data, header_start + 2 + 4)[0]
        if section_id != 0:
            raise MalformedFileError(
                f"SCP-ECG file {scp_file.name} does not begin with Section 0 (found section id {section_id})."
            )

        section0_length = struct.unpack_from("<I", data, header_start + 2)[0]
        pointer_data_start = header_start + _SECTION_HEADER_LEN
        pointer_data_end = header_start + section0_length
        if pointer_data_end > len(data) or pointer_data_end < pointer_data_start:
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} has an invalid Section 0 length.")

        sections: dict[int, tuple[int, int]] = {}
        offset = pointer_data_start
        while offset + _POINTER_ENTRY_LEN <= pointer_data_end:
            sec_id, sec_len, sec_index = struct.unpack_from("<HII", data, offset)
            if sec_id != 0 and sec_len > 0:
                sections[sec_id] = (sec_index, sec_len)
            offset += _POINTER_ENTRY_LEN

        if not sections:
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} declares no sections in its pointer table.")
        return sections

    # -- section 1: patient / recording tags ---------------------------------

    @staticmethod
    def _parse_section1(data: bytes, section: tuple[int, int]) -> tuple[dict[str, str], dict[str, str]]:
        start, length = section
        body_start = start + _SECTION_HEADER_LEN
        body_end = start + length
        if body_end > len(data):
            return {}, {}

        patient_info: dict[str, str] = {}
        other_tags: dict[str, str] = {}
        offset = body_start
        while offset + 3 <= body_end:
            tag = data[offset]
            if tag == 255:
                break
            tag_len = struct.unpack_from("<H", data, offset + 1)[0]
            value_start = offset + 3
            value_end = value_start + tag_len
            if value_end > body_end:
                break
            raw_value = data[value_start:value_end]
            field_name = _SECTION1_PATIENT_TAGS.get(tag)
            if field_name:
                patient_info[field_name] = raw_value.split(b"\x00", 1)[0].decode("latin-1", errors="replace").strip()
            else:
                other_tags[f"tag_{tag}"] = raw_value.hex()
            offset = value_end
        return patient_info, other_tags

    # -- section 3: lead definitions ------------------------------------------

    @staticmethod
    def _parse_section3(data: bytes, section: tuple[int, int], scp_file: Path) -> list[CanonicalLead]:
        start, length = section
        body_start = start + _SECTION_HEADER_LEN
        if body_start >= len(data):
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} has an empty Section 3.")

        num_leads = data[body_start]
        entry_start = body_start + 1
        leads: list[CanonicalLead] = []
        for i in range(num_leads):
            entry_offset = entry_start + i * 9
            if entry_offset + 9 > start + length:
                raise MalformedFileError(f"SCP-ECG file {scp_file.name} Section 3 is truncated.")
            lead_id = data[entry_offset + 8]
            canonical = _SCP_LEAD_ID_TO_CANONICAL.get(lead_id)
            if canonical is None:
                raise UnmappableLeadError(
                    f"SCP-ECG lead identification code {lead_id} in {scp_file.name} has no canonical NCEP mapping."
                )
            leads.append(canonical)

        if not leads:
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} Section 3 declares zero leads.")
        return leads

    # -- section 6: rhythm data ------------------------------------------------

    @classmethod
    def _parse_section6(
        cls, data: bytes, section: tuple[int, int], lead_order: list[CanonicalLead], scp_file: Path
    ) -> Waveform:
        start, length = section
        body_start = start + _SECTION_HEADER_LEN
        body_end = start + length
        if body_start + 6 > body_end:
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} Section 6 header is truncated.")

        avm_nanovolts, sample_interval_us, difference_order, bimodal_flag = struct.unpack_from(
            "<HHBB", data, body_start
        )
        if bimodal_flag:
            raise UnsupportedVersionError(
                f"SCP-ECG file {scp_file.name} uses Huffman (bimodal) compressed rhythm data, which is not supported."
            )
        if difference_order not in (0, 1, 2):
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} has an unrecognized difference order {difference_order}.")
        if sample_interval_us <= 0:
            raise MalformedFileError(f"SCP-ECG file {scp_file.name} has a non-positive sample interval.")

        sampling_rate_hz = 1_000_000.0 / sample_interval_us
        amplitude_scale_mv = avm_nanovolts / 1_000_000.0  # nanovolts -> millivolts per LSB

        offset = body_start + 6
        leads: dict[CanonicalLead, LeadSignal] = {}
        for canonical in lead_order:
            if offset + 2 > body_end:
                raise MalformedFileError(f"SCP-ECG file {scp_file.name} Section 6 is truncated before lead {canonical.value}.")
            byte_len = struct.unpack_from("<H", data, offset)[0]
            offset += 2
            if offset + byte_len > body_end:
                raise MalformedFileError(f"SCP-ECG file {scp_file.name} Section 6 lead {canonical.value} data is truncated.")
            raw_bytes = data[offset : offset + byte_len]
            offset += byte_len

            samples = cls._decode_lead_samples(raw_bytes, difference_order, scp_file, canonical)
            leads[canonical] = LeadSignal(canonical, samples * amplitude_scale_mv)

        return Waveform(leads=leads, sampling_rate_hz=sampling_rate_hz, units=DEFAULT_SIGNAL_UNITS)

    @staticmethod
    def _decode_lead_samples(raw_bytes: bytes, difference_order: int, scp_file: Path, lead: CanonicalLead) -> np.ndarray:
        if difference_order == 0:
            if len(raw_bytes) % 2 != 0:
                raise MalformedFileError(f"SCP-ECG file {scp_file.name} lead {lead.value} has an odd byte count for uncompressed samples.")
            return np.frombuffer(raw_bytes, dtype="<i2").astype(np.float64)

        # Difference-encoded as signed byte deltas (order 1 = first
        # difference, order 2 = second difference); reconstructed via
        # cumulative sum.
        deltas = np.frombuffer(raw_bytes, dtype=np.int8).astype(np.float64)
        reconstructed = np.cumsum(deltas)
        if difference_order == 2:
            reconstructed = np.cumsum(reconstructed)
        return reconstructed
