"""WFDB Parser.

Purpose:
    Reads WFDB recordings (.hea plus referenced signal/annotation files),
    extracts waveform and raw metadata, and constructs a ParsedECG. This is
    the Phase 1 reference parser implementation, developed and tested
    against the PTB Diagnostic ECG Database (PhysioNet) but not hardcoded
    to it (Implementation Spec 8.18, 10.9).

Responsibilities:
    - Verify a header file is present.
    - Read header + signal via the `wfdb` package (which transparently
      follows whatever signal/annotation files the header references --
      one or several, any extension).
    - Map source lead names to canonical NCEP leads.
    - Read WFDB annotation files when present.
    - Extract raw header comments for downstream metadata extraction.
    - Build ParsedECG.

Shall NOT:
    - Validate the ECG.
    - Filter the signal.
    - Detect beats.
    - Calculate biomarkers.

Input:
    The set of uploaded files belonging to one WFDB recording.

Output:
    ParsedECG

Dependencies:
    wfdb, Waveform, ParsedECG, app.ecg.lead_mapping

Exceptions:
    MissingRequiredFileError, MalformedFileError, UnmappableLeadError
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import wfdb

from app.ecg.constants import DEFAULT_SIGNAL_UNITS, ECGFormat, CanonicalLead
from app.ecg.lead_mapping import resolve_canonical_lead
from app.ecg.models.annotations import Annotation, AnnotationType
from app.ecg.models.waveform import LeadSignal, Waveform
from app.ingestion.exceptions import MalformedFileError, MissingRequiredFileError
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.interfaces.parser import ParserInterface

# WFDB header comment keys that describe the patient rather than the
# recording. Generic to the WFDB comment convention, not specific to any
# one dataset (Business Rule 8.18 -- Development Dataset Independence).
_PATIENT_COMMENT_KEYS = {"age", "sex", "gender", "name", "patient", "id", "dob", "date of birth", "patient id"}


class WFDBParser(ParserInterface):
    """Parses WFDB-format ECG recordings into ParsedECG."""

    format = ECGFormat.WFDB

    def can_parse(self, files: Sequence[Path]) -> bool:
        return any(Path(f).suffix.lower() == ".hea" for f in files)

    def parse(self, files: Sequence[Path]) -> ParsedECG:
        file_list = [Path(f) for f in files]
        header_files = [f for f in file_list if f.suffix.lower() == ".hea"]

        if not header_files:
            raise MissingRequiredFileError("WFDB parsing requires a .hea header file.")
        if len(header_files) > 1:
            raise MalformedFileError(
                "Multiple .hea files were provided; one WFDB upload must represent exactly one recording."
            )

        header_file = header_files[0]
        record_dir = header_file.parent
        record_name = header_file.stem

        record = self._read_record(record_dir, record_name, header_file)
        waveform = self._build_waveform(record, record_name)
        raw_patient_info, raw_clinical_info = self._split_comments(record.comments)

        raw_recording_info = {
            "record_name": record_name,
            "base_date": getattr(record, "base_date", None),
            "base_time": getattr(record, "base_time", None),
            "comments": list(record.comments or []),
            "sig_name": list(record.sig_name or []),
        }

        annotations = self._read_annotations(file_list, record, record_dir, record_name)

        return ParsedECG(
            source_format=ECGFormat.WFDB,
            source_files=tuple(file_list),
            parser_name="WFDBParser",
            waveform=waveform,
            raw_patient_info=raw_patient_info,
            raw_recording_info=raw_recording_info,
            raw_clinical_info=raw_clinical_info,
            raw_device_info={},
            raw_quality_info={},
            raw_annotations=annotations,
        )

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _read_record(record_dir: Path, record_name: str, header_file: Path):
        try:
            return wfdb.rdrecord(str(record_dir / record_name))
        except FileNotFoundError as exc:
            raise MissingRequiredFileError(
                f"A signal file referenced by {header_file.name} is missing: {exc}"
            ) from exc
        except Exception as exc:  # wfdb raises plain Exception/ValueError for malformed headers
            raise MalformedFileError(f"Failed to read WFDB record for {header_file.name}: {exc}") from exc

    @staticmethod
    def _build_waveform(record, record_name: str) -> Waveform:
        signal = record.p_signal
        if signal is None:
            signal = record.d_signal
        if signal is None or not record.sig_name:
            raise MalformedFileError(f"WFDB record {record_name!r} contains no signal data.")

        leads: dict[CanonicalLead, LeadSignal] = {}
        for idx, raw_name in enumerate(record.sig_name):
            canonical = resolve_canonical_lead(raw_name)
            if canonical in leads:
                raise MalformedFileError(f"Duplicate canonical lead {canonical.value} in WFDB record {record_name!r}.")
            leads[canonical] = LeadSignal(canonical, np.asarray(signal[:, idx], dtype=np.float64))

        units = None
        if record.units:
            non_empty = [u for u in record.units if u]
            units = non_empty[0] if non_empty else None

        return Waveform(leads=leads, sampling_rate_hz=float(record.fs), units=units or DEFAULT_SIGNAL_UNITS)

    @staticmethod
    def _split_comments(comments: list[str] | None) -> tuple[dict[str, str], dict[str, str]]:
        patient_info: dict[str, str] = {}
        clinical_info: dict[str, str] = {}
        for line in comments or []:
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key_norm = key.strip().lstrip("#").strip().lower()
            value = value.strip()
            if not key_norm or not value:
                continue
            bucket = patient_info if key_norm in _PATIENT_COMMENT_KEYS else clinical_info
            bucket[key_norm] = value
        return patient_info, clinical_info

    @staticmethod
    def _read_annotations(
        file_list: list[Path], record, record_dir: Path, record_name: str
    ) -> tuple[Annotation, ...]:
        signal_exts = {Path(name).suffix.lower().lstrip(".") for name in (record.file_name or [])}
        uploaded_exts = {f.suffix.lower().lstrip(".") for f in file_list} - {"hea"} - signal_exts

        fs = float(record.fs) if record.fs else None
        annotations: list[Annotation] = []
        for ext in sorted(uploaded_exts):
            try:
                ann = wfdb.rdann(str(record_dir / record_name), ext)
            except Exception:
                # Optional companion file that is not a readable WFDB
                # annotation file for this record -- continue (Implementation
                # Spec: "continue when optional files are absent").
                continue
            for sample, symbol in zip(ann.sample, ann.symbol):
                annotations.append(
                    Annotation(
                        annotation_type=AnnotationType.BEAT,
                        label=str(symbol),
                        sample_index=int(sample),
                        time_offset_seconds=(float(sample) / fs) if fs else None,
                        source=f"wfdb:.{ext}",
                    )
                )
        return tuple(annotations)
