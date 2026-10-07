"""Unit tests for the Format Detector."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ecg.constants import ECGFormat
from app.ingestion.detectors.format_detector import detect_format
from app.ingestion.exceptions import FormatDetectionError


def test_detect_wfdb(wfdb_sample_dir: list[Path]) -> None:
    assert detect_format(wfdb_sample_dir) == ECGFormat.WFDB


def test_detect_csv(csv_sample_file: Path) -> None:
    assert detect_format([csv_sample_file]) == ECGFormat.CSV


def test_detect_xml(xml_sample_file: Path) -> None:
    assert detect_format([xml_sample_file]) == ECGFormat.XML


def test_detect_dicom(dicom_sample_file: Path) -> None:
    assert detect_format([dicom_sample_file]) == ECGFormat.DICOM


def test_detect_scp(scp_sample_file: Path) -> None:
    assert detect_format([scp_sample_file]) == ECGFormat.SCP_ECG


def test_detect_format_raises_on_no_files() -> None:
    with pytest.raises(FormatDetectionError):
        detect_format([])


def test_detect_format_raises_on_unsupported_extension(tmp_path: Path) -> None:
    unknown_file = tmp_path / "recording.unknownfmt"
    unknown_file.write_bytes(b"not a real ecg file")
    with pytest.raises(FormatDetectionError):
        detect_format([unknown_file])


def test_detect_format_dicom_by_magic_bytes_without_extension(tmp_path: Path) -> None:
    dicom_like = tmp_path / "recording.bin"
    dicom_like.write_bytes(b"\x00" * 128 + b"DICM" + b"\x00" * 20)
    assert detect_format([dicom_like]) == ECGFormat.DICOM


# -- Mixed-format (ambiguous) upload rejection -------------------------------------------------------------


def test_detect_format_rejects_wfdb_header_mixed_with_unrelated_csv(
    wfdb_sample_dir: list[Path], csv_sample_file: Path
) -> None:
    """A .hea/.dat pair plus an unrelated .csv file must never silently resolve to WFDB."""
    with pytest.raises(FormatDetectionError):
        detect_format([*wfdb_sample_dir, csv_sample_file])


def test_detect_format_rejects_xml_mixed_with_dicom(xml_sample_file: Path, dicom_sample_file: Path) -> None:
    with pytest.raises(FormatDetectionError):
        detect_format([xml_sample_file, dicom_sample_file])


def test_detect_format_rejects_csv_mixed_with_scp(csv_sample_file: Path, scp_sample_file: Path) -> None:
    with pytest.raises(FormatDetectionError):
        detect_format([csv_sample_file, scp_sample_file])


def test_detect_format_error_message_names_the_conflicting_formats(
    wfdb_sample_dir: list[Path], csv_sample_file: Path
) -> None:
    with pytest.raises(FormatDetectionError) as exc_info:
        detect_format([*wfdb_sample_dir, csv_sample_file])
    message = str(exc_info.value)
    assert "WFDB" in message
    assert "CSV" in message


def test_detect_format_wfdb_companion_files_do_not_trigger_false_ambiguity(wfdb_sample_dir: list[Path]) -> None:
    """WFDB signal/annotation companion files (.dat, .atr, ...) never register their own
    format on their own -- an ordinary WFDB upload must still resolve cleanly."""
    assert detect_format(wfdb_sample_dir) == ECGFormat.WFDB


def test_detect_format_names_missing_hea_when_only_companions_are_uploaded(wfdb_sample_dir: list[Path]) -> None:
    """A WFDB companion file (e.g. .dat) uploaded without its .hea header is a common
    mistake (selecting only one of several required files) -- the error must say so
    explicitly rather than the generic "unrecognized format" message."""
    companions_only = [f for f in wfdb_sample_dir if f.suffix.lower() != ".hea"]
    assert companions_only, "fixture must include at least one non-.hea companion file"
    with pytest.raises(FormatDetectionError) as exc_info:
        detect_format(companions_only)
    message = str(exc_info.value)
    assert ".hea" in message
    assert companions_only[0].name in message
