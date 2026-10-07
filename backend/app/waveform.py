"""Parsing helpers for uploaded ECG/SAECG waveform CSVs and their metadata sidecars.

Expected demo bundle (from backend/sample_file):
  - waveform.csv          columns: sample_index, time_s, <lead columns...>
  - ecg_metadata.json     recording metadata (sampling rate, leads, duration, ...)
  - patient_metadata.json patient demographics
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field

NON_LEAD_COLUMNS = {"sample_index", "time_s", "time", "index", "t"}


@dataclass
class WaveformMeta:
    source_format: str | None = None
    sampling_rate_hz: float | None = None
    lead_count: int | None = None
    available_leads: list[str] = field(default_factory=list)
    xyz_available: bool = False
    duration_seconds: float | None = None
    sample_count: int | None = None
    units: str | None = None
    record_id: str | None = None


def parse_ecg_metadata(raw: bytes | str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def inspect_csv_header(path: str) -> tuple[list[str], int]:
    """Return (lead_names, data_row_count) by scanning the CSV once."""
    leads: list[str] = []
    rows = 0
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        leads = [c for c in header if c.strip().lower() not in NON_LEAD_COLUMNS]
        for _ in reader:
            rows += 1
    return leads, rows


def build_meta(path: str, ecg_meta: dict) -> WaveformMeta:
    """Merge sidecar metadata with values inferred from the CSV itself."""
    leads, row_count = inspect_csv_header(path)
    available_leads = ecg_meta.get("available_leads") or leads
    lead_count = ecg_meta.get("lead_count") or len(available_leads)
    sampling_rate = ecg_meta.get("sampling_rate_hz")
    sample_count = ecg_meta.get("sample_count") or row_count
    duration = ecg_meta.get("recording_duration_seconds")
    if duration is None and sampling_rate and sample_count:
        duration = round(sample_count / sampling_rate, 3)
    xyz = ecg_meta.get("xyz_available")
    if xyz is None:
        xyz = all(ax in available_leads for ax in ("X", "Y", "Z"))
    return WaveformMeta(
        source_format=ecg_meta.get("source_format"),
        sampling_rate_hz=sampling_rate,
        lead_count=lead_count,
        available_leads=available_leads,
        xyz_available=bool(xyz),
        duration_seconds=duration,
        sample_count=sample_count,
        units=ecg_meta.get("units"),
        record_id=ecg_meta.get("record_id"),
    )


def read_waveform(
    path: str,
    requested_leads: list[str] | None,
    max_points: int,
    known_sample_count: int | None = None,
) -> tuple[list[str], list[float], dict[str, list[float]], int]:
    """Stream the CSV and return downsampled (leads, time_s, signals, factor).

    Downsamples by striding so large recordings stay light for the viewer, without
    ever materializing the whole file in memory. `known_sample_count` (e.g. from
    `ECGRecord.sample_count`) lets the stride be computed up front for a true
    single streaming pass; without it, a cheap counting-only pre-pass is used
    (still O(1) memory, unlike buffering every row).
    """
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        col_index = {name: i for i, name in enumerate(header)}
        all_leads = [c for c in header if c.strip().lower() not in NON_LEAD_COLUMNS]
        leads = [l for l in (requested_leads or all_leads) if l in col_index] or all_leads
        time_col = next((c for c in ("time_s", "time", "t") if c in col_index), None)

        total = known_sample_count
        if total is None:
            total = sum(1 for _ in reader)
            f.seek(0)
            reader = csv.reader(f)
            next(reader, [])

        factor = max(1, total // max_points) if max_points > 0 else 1

        time_s: list[float] = []
        signals: dict[str, list[float]] = {l: [] for l in leads}
        for i, row in enumerate(reader):
            if i % factor != 0:
                continue
            if time_col is not None:
                try:
                    time_s.append(float(row[col_index[time_col]]))
                except (ValueError, IndexError):
                    time_s.append(i)
            else:
                time_s.append(i)
            for l in leads:
                try:
                    signals[l].append(float(row[col_index[l]]))
                except (ValueError, IndexError):
                    signals[l].append(0.0)

    return leads, time_s, signals, factor
