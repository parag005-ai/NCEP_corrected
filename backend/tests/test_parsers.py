"""Unit tests for the format-specific parsers.

Each parser is exercised for: happy path, invalid/missing input, and
corrupted content, per the Implementation Spec's Unit Test Checklist.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.ecg.constants import CanonicalLead, ECGFormat
from app.ingestion.exceptions import (
    MalformedFileError,
    MissingRequiredFileError,
    UnmappableLeadError,
    UnsupportedVersionError,
)
from app.ingestion.factories.parser_factory import get_parser
from app.ingestion.parsers.csv.parser import CSVParser
from app.ingestion.parsers.dicom.parser import DICOMParser
from app.ingestion.parsers.scp.parser import SCPParser
from app.ingestion.parsers.wfdb.parser import WFDBParser
from app.ingestion.parsers.xml.parser import XMLParser
from tests.conftest import build_scp_bytes


# -- WFDB -------------------------------------------------------------


def test_wfdb_parser_happy_path(wfdb_sample_dir: list[Path]) -> None:
    parsed = WFDBParser().parse(wfdb_sample_dir)
    assert parsed.parser_name == "WFDBParser"
    assert parsed.waveform.lead_count == 15
    assert parsed.waveform.xyz_available is True
    assert parsed.waveform.sampling_rate_hz == 500.0
    assert parsed.raw_patient_info["age"] == "81"
    assert parsed.raw_patient_info["sex"] == "male"
    assert parsed.raw_clinical_info["reason for admission"] == "Myocardial infarction"


def test_wfdb_parser_missing_header_raises(wfdb_sample_dir: list[Path]) -> None:
    dat_only = [f for f in wfdb_sample_dir if f.suffix != ".hea"]
    with pytest.raises(MissingRequiredFileError):
        WFDBParser().parse(dat_only)


def test_wfdb_parser_missing_signal_file_raises(wfdb_sample_dir: list[Path], tmp_path: Path) -> None:
    hea_only_dir = tmp_path / "hea_only"
    hea_only_dir.mkdir()
    hea_file = next(f for f in wfdb_sample_dir if f.suffix == ".hea")
    copied = hea_only_dir / hea_file.name
    copied.write_bytes(hea_file.read_bytes())
    with pytest.raises(MissingRequiredFileError):
        WFDBParser().parse([copied])


def test_wfdb_parser_multiple_headers_raises(wfdb_sample_dir: list[Path], tmp_path: Path) -> None:
    hea_file = next(f for f in wfdb_sample_dir if f.suffix == ".hea")
    duplicate = tmp_path / "duplicate.hea"
    duplicate.write_bytes(hea_file.read_bytes())
    with pytest.raises(MalformedFileError):
        WFDBParser().parse([*wfdb_sample_dir, duplicate])


def test_wfdb_parser_automatically_associates_arbitrary_annotation_extension(wfdb_sample_dir: list[Path]) -> None:
    """The parser must associate companion annotation files by whatever extension is
    actually uploaded, not a hardcoded list -- proving it is standards-based rather
    than tied to any one dataset's conventions (e.g. PTB's ".atr")."""
    import wfdb

    record_dir = wfdb_sample_dir[0].parent
    record_name = wfdb_sample_dir[0].stem

    wfdb.wrann(
        record_name,
        "mkr",
        sample=np.array([10, 200, 500]),
        symbol=["N", "N", "V"],
        write_dir=str(record_dir),
    )
    annotation_file = record_dir / f"{record_name}.mkr"

    parsed = WFDBParser().parse([*wfdb_sample_dir, annotation_file])

    assert len(parsed.raw_annotations) == 3
    assert {a.label for a in parsed.raw_annotations} == {"N", "V"}
    assert all(a.source == "wfdb:.mkr" for a in parsed.raw_annotations)


# -- CSV -------------------------------------------------------------


def test_csv_parser_happy_path(csv_sample_file: Path) -> None:
    parsed = CSVParser().parse([csv_sample_file])
    assert parsed.waveform.lead_count == 3
    assert parsed.waveform.sampling_rate_hz == 250.0
    assert parsed.raw_patient_info["patient_id"] == "PT-001"
    assert parsed.raw_clinical_info["diagnosis"] == "sinus rhythm"


def test_csv_parser_derives_sampling_rate_from_time_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "notime_comment.csv"
    lines = ["time,I"] + [f"{i / 500.0:.5f},{i * 0.001:.5f}" for i in range(100)]
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    parsed = CSVParser().parse([csv_path])
    assert parsed.waveform.sampling_rate_hz == pytest.approx(500.0, rel=1e-2)


def test_csv_parser_missing_file_raises() -> None:
    with pytest.raises(MissingRequiredFileError):
        CSVParser().parse([])


def test_csv_parser_unmappable_lead_column_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad_columns.csv"
    csv_path.write_text("time,NOTALEAD\n0.0,1.0\n0.002,2.0\n", encoding="utf-8")
    with pytest.raises(UnmappableLeadError):
        CSVParser().parse([csv_path])


def test_csv_parser_no_sampling_rate_available_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "no_rate.csv"
    csv_path.write_text("I,II\n0.1,0.2\n0.3,0.4\n", encoding="utf-8")
    with pytest.raises(MalformedFileError):
        CSVParser().parse([csv_path])


def test_csv_parser_empty_file_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")
    with pytest.raises(MalformedFileError):
        CSVParser().parse([csv_path])


# -- XML -------------------------------------------------------------


def test_xml_parser_happy_path(xml_sample_file: Path) -> None:
    parsed = XMLParser().parse([xml_sample_file])
    assert parsed.waveform.lead_count == 2
    assert parsed.raw_patient_info["name"] == "Jane Doe"
    assert parsed.raw_clinical_info["medications"] == ["aspirin"]
    assert len(parsed.raw_annotations) == 1


def test_xml_parser_malformed_xml_raises(tmp_path: Path) -> None:
    xml_path = tmp_path / "bad.xml"
    xml_path.write_text("<ECG><Leads><Lead name='I'>not closed", encoding="utf-8")
    with pytest.raises(MalformedFileError):
        XMLParser().parse([xml_path])


def test_xml_parser_missing_leads_raises(tmp_path: Path) -> None:
    xml_path = tmp_path / "no_leads.xml"
    xml_path.write_text('<ECG><RecordingInfo samplingRateHz="500"/></ECG>', encoding="utf-8")
    with pytest.raises(MalformedFileError):
        XMLParser().parse([xml_path])


def test_xml_parser_missing_sampling_rate_raises(tmp_path: Path) -> None:
    xml_path = tmp_path / "no_rate.xml"
    xml_path.write_text("<ECG><Leads><Lead name='I'>0.1,0.2,0.3</Lead></Leads></ECG>", encoding="utf-8")
    with pytest.raises(MalformedFileError):
        XMLParser().parse([xml_path])


# -- DICOM -------------------------------------------------------------


def test_dicom_parser_happy_path(dicom_sample_file: Path) -> None:
    parsed = DICOMParser().parse([dicom_sample_file])
    assert parsed.waveform.lead_count == 3
    assert CanonicalLead.V1 in parsed.waveform.leads
    assert parsed.raw_patient_info["patient_id"] == "PID-77"
    assert parsed.raw_device_info["manufacturer"] == "Acme Medical"


def test_dicom_parser_non_dicom_file_raises(tmp_path: Path) -> None:
    fake = tmp_path / "fake.dcm"
    fake.write_bytes(b"not a real dicom file")
    with pytest.raises(MalformedFileError):
        DICOMParser().parse([fake])


def test_dicom_parser_missing_file_raises() -> None:
    with pytest.raises(MissingRequiredFileError):
        DICOMParser().parse([])


def test_dicom_parser_combines_study_date_and_time(tmp_path: Path) -> None:
    from tests.conftest import build_dicom_dataset

    dcm_path = build_dicom_dataset(tmp_path, StudyDate="20250131", StudyTime="143000")
    parsed = DICOMParser().parse([dcm_path])
    assert parsed.raw_recording_info["acquisition_timestamp"] == "20250131143000"


def test_dicom_parser_handles_date_only_value(tmp_path: Path) -> None:
    """A DICOM recording with a StudyDate but no StudyTime must still yield a usable
    acquisition timestamp (the date), rather than silently dropping it."""
    from tests.conftest import build_dicom_dataset

    from app.ingestion.metadata.ecg.extractor import ECGMetadataExtractor

    dcm_path = build_dicom_dataset(tmp_path, StudyDate="20250131")
    parsed = DICOMParser().parse([dcm_path])
    assert parsed.raw_recording_info["acquisition_timestamp"] == "20250131"

    ecg_metadata = ECGMetadataExtractor.extract(parsed, record_id="rec-date-only")
    assert ecg_metadata.acquisition_timestamp is not None
    assert ecg_metadata.acquisition_timestamp.date().isoformat() == "2025-01-31"


def test_dicom_parser_prefers_acquisition_datetime_over_study_date(tmp_path: Path) -> None:
    from tests.conftest import build_dicom_dataset

    dcm_path = build_dicom_dataset(
        tmp_path,
        StudyDate="20250101",
        StudyTime="000000",
        AcquisitionDateTime="20250215091500.000000",
    )
    parsed = DICOMParser().parse([dcm_path])
    assert parsed.raw_recording_info["acquisition_timestamp"] == "20250215091500"


# -- SCP-ECG -------------------------------------------------------------


def test_scp_parser_happy_path(scp_sample_file: Path) -> None:
    parsed = SCPParser().parse([scp_sample_file])
    assert parsed.waveform.lead_count == 3
    assert parsed.raw_patient_info["last_name"] == "Doe"
    assert parsed.raw_patient_info["patient_id"] == "PID-555"


def test_scp_parser_decodes_amplitude_correctly(scp_sample_file: Path) -> None:
    _, expected, expected_fs = build_scp_bytes()
    parsed = SCPParser().parse([scp_sample_file])
    assert parsed.waveform.sampling_rate_hz == pytest.approx(expected_fs)
    actual = parsed.waveform.leads[CanonicalLead.I].samples
    assert np.allclose(actual, expected["I"])


def test_scp_parser_rejects_huffman_compressed_data(scp_sample_file: Path) -> None:
    data = bytearray(scp_sample_file.read_bytes())
    # Locate the section 6 bimodal-compression flag and set it -- rather than
    # hardcoding an offset, search for the section-6 pointer entry.
    import struct

    header_start = 6
    section0_len = struct.unpack_from("<I", data, header_start + 2)[0]
    offset = header_start + 16
    end = header_start + section0_len
    section6_start = None
    while offset + 10 <= end:
        sec_id, sec_len, sec_index = struct.unpack_from("<HII", data, offset)
        if sec_id == 6:
            section6_start = sec_index
        offset += 10
    assert section6_start is not None
    bimodal_flag_offset = section6_start + 16 + 5  # header(16) + avm(2)+interval(2)+diff(1) -> bimodal byte
    data[bimodal_flag_offset] = 1
    corrupted_path = scp_sample_file.parent / "huffman.scp"
    corrupted_path.write_bytes(bytes(data))
    with pytest.raises(UnsupportedVersionError):
        SCPParser().parse([corrupted_path])


def test_scp_parser_missing_file_raises() -> None:
    with pytest.raises(MissingRequiredFileError):
        SCPParser().parse([])


def test_scp_parser_truncated_file_raises(tmp_path: Path) -> None:
    truncated = tmp_path / "truncated.scp"
    truncated.write_bytes(b"\x00\x00\x10\x00\x00\x00")
    with pytest.raises(MalformedFileError):
        SCPParser().parse([truncated])


# -- Parser Factory integration -------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name,expected_format",
    [
        ("wfdb_sample_dir", ECGFormat.WFDB),
        ("csv_sample_file", ECGFormat.CSV),
        ("xml_sample_file", ECGFormat.XML),
        ("dicom_sample_file", ECGFormat.DICOM),
        ("scp_sample_file", ECGFormat.SCP_ECG),
    ],
)
def test_parser_factory_returns_correct_parser(fixture_name: str, expected_format: ECGFormat, request) -> None:
    parser = get_parser(expected_format)
    assert parser.format == expected_format
