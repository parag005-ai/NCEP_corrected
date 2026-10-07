"""CSV Parser.

Purpose:
    Reads ECG recordings already stored as tabular waveform data and
    constructs a ParsedECG (Implementation Spec 10.13).

Responsibilities:
    - Identify available leads from the CSV header row.
    - Interpret sampling information when provided.
    - Extract accompanying metadata (leading `# key: value` comment lines)
      when available.
    - Build ParsedECG.

Shall NOT:
    - Validate the ECG.
    - Filter the signal.
    - Fabricate a sampling rate when none can be determined.

Input:
    A single uploaded .csv file. Column headers name the leads present
    (e.g. I, II, V1); an optional time/timestamp column is used to derive
    the sampling rate when it is not supplied as metadata.

Output:
    ParsedECG

Exceptions:
    MissingRequiredFileError, MalformedFileError, UnmappableLeadError
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

from app.ecg.constants import DEFAULT_SIGNAL_UNITS, ECGFormat, CanonicalLead
from app.ecg.lead_mapping import resolve_canonical_lead
from app.ecg.models.waveform import LeadSignal, Waveform
from app.ingestion.exceptions import MalformedFileError, MissingRequiredFileError
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.interfaces.parser import ParserInterface

_TIME_COLUMN_ALIASES = {"time", "timestamp", "t", "time_s", "time_sec", "seconds"}
_INDEX_COLUMN_ALIASES = {"sample_index", "index"}
_PATIENT_INFO_KEYS = {"age", "sex", "gender", "name", "patient", "patient_id", "id", "dob", "date of birth"}


class CSVParser(ParserInterface):
    """Parses tabular (CSV) ECG recordings into ParsedECG."""

    format = ECGFormat.CSV

    def can_parse(self, files: Sequence[Path]) -> bool:
        return any(Path(f).suffix.lower() == ".csv" for f in files)

    def parse(self, files: Sequence[Path]) -> ParsedECG:
        file_list = [Path(f) for f in files]
        csv_files = [f for f in file_list if f.suffix.lower() == ".csv"]

        if not csv_files:
            raise MissingRequiredFileError("CSV parsing requires at least one .csv file.")
        if len(csv_files) > 1:
            raise MalformedFileError(
                "Multiple .csv files were provided; one CSV upload must represent exactly one recording."
            )
        csv_file = csv_files[0]

        metadata_comments, skip_rows = self._read_leading_comments(csv_file)

        try:
            frame = pd.read_csv(csv_file, skiprows=skip_rows)
        except Exception as exc:
            raise MalformedFileError(f"Failed to read CSV file {csv_file.name}: {exc}") from exc

        if frame.empty or frame.shape[1] == 0:
            raise MalformedFileError(f"CSV file {csv_file.name} contains no data.")

        time_column = next(
            (col for col in frame.columns if str(col).strip().lower() in _TIME_COLUMN_ALIASES), None
        )

        leads: dict[CanonicalLead, LeadSignal] = {}
        for column in frame.columns:
            if column == time_column or str(column).strip().lower() in _INDEX_COLUMN_ALIASES:
                continue
            canonical = resolve_canonical_lead(str(column))
            if canonical in leads:
                raise MalformedFileError(f"Duplicate canonical lead {canonical.value} in CSV columns of {csv_file.name}.")
            values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=np.float64)
            leads[canonical] = LeadSignal(canonical, values)

        if not leads:
            raise MalformedFileError(f"No recognizable ECG lead columns found in {csv_file.name}.")

        sampling_rate_hz = self._resolve_sampling_rate(metadata_comments, frame, time_column, csv_file)
        units = metadata_comments.get("units") or DEFAULT_SIGNAL_UNITS

        waveform = Waveform(leads=leads, sampling_rate_hz=sampling_rate_hz, units=units)

        raw_patient_info = {k: v for k, v in metadata_comments.items() if k in _PATIENT_INFO_KEYS}
        raw_clinical_info = {
            k: v for k, v in metadata_comments.items() if k not in _PATIENT_INFO_KEYS and k not in {"units", "sampling_rate_hz", "sampling_rate"}
        }

        return ParsedECG(
            source_format=ECGFormat.CSV,
            source_files=tuple(file_list),
            parser_name="CSVParser",
            waveform=waveform,
            raw_patient_info=raw_patient_info,
            raw_recording_info=dict(metadata_comments),
            raw_clinical_info=raw_clinical_info,
            raw_device_info={},
            raw_quality_info={},
            raw_annotations=(),
        )

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _read_leading_comments(csv_file: Path) -> tuple[dict[str, str], int]:
        comments: dict[str, str] = {}
        skip = 0
        with csv_file.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped.startswith("#"):
                    break
                skip += 1
                body = stripped.lstrip("#").strip()
                if ":" in body:
                    key, _, value = body.partition(":")
                    comments[key.strip().lower()] = value.strip()
        return comments, skip

    @staticmethod
    def _resolve_sampling_rate(
        metadata_comments: dict[str, str], frame: pd.DataFrame, time_column: str | None, csv_file: Path
    ) -> float:
        for key in ("sampling_rate_hz", "sampling_rate"):
            if key in metadata_comments:
                try:
                    return float(metadata_comments[key])
                except ValueError:
                    continue

        if time_column is not None:
            times = pd.to_numeric(frame[time_column], errors="coerce").to_numpy(dtype=np.float64)
            diffs = np.diff(times)
            diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
            if diffs.size:
                return float(1.0 / np.median(diffs))

        raise MalformedFileError(
            f"Unable to determine sampling rate for {csv_file.name}: provide a '# sampling_rate_hz: <value>' "
            "header comment or a time/timestamp column."
        )
