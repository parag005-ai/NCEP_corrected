"""Shared pytest fixtures for building synthetic ECG source files.

No real patient data is used anywhere in this suite. WFDB fixtures follow
the PTB Diagnostic ECG Database layout (12 standard leads + Frank X/Y/Z)
since that is Phase 1's reference dataset; the other formats use the
generic schemas documented in their respective parser modules.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def wfdb_sample_dir(tmp_path: Path) -> list[Path]:
    import wfdb

    fs = 500
    n = 1000
    sig_names = ["i", "ii", "iii", "avr", "avl", "avf", "v1", "v2", "v3", "v4", "v5", "v6", "vx", "vy", "vz"]
    rng = np.random.default_rng(0)
    signal = rng.normal(0, 0.5, size=(n, len(sig_names))).astype(np.float64)

    out_dir = tmp_path / "wfdb"
    out_dir.mkdir()
    wfdb.wrsamp(
        record_name="ptbsample",
        fs=fs,
        units=["mV"] * len(sig_names),
        sig_name=sig_names,
        p_signal=signal,
        fmt=["16"] * len(sig_names),
        write_dir=str(out_dir),
        comments=["age: 81", "sex: male", "Reason for admission: Myocardial infarction"],
    )
    return sorted(out_dir.glob("ptbsample.*"))


@pytest.fixture
def csv_sample_file(tmp_path: Path) -> Path:
    csv_path = tmp_path / "record.csv"
    lines = [
        "# sampling_rate_hz: 250",
        "# patient_id: PT-001",
        "# diagnosis: sinus rhythm",
        "time,I,II,V1",
    ]
    n = 200
    for i in range(n):
        t = i / 250.0
        lines.append(f"{t:.4f},{(0.01 * i) % 1:.5f},{(0.02 * i) % 1:.5f},{(0.03 * i) % 1:.5f}")
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path


@pytest.fixture
def xml_sample_file(tmp_path: Path) -> Path:
    xml_path = tmp_path / "record.xml"
    n = 200
    lead_i = ",".join(f"{i * 0.001:.5f}" for i in range(n))
    lead_ii = ",".join(f"{i * 0.002:.5f}" for i in range(n))
    xml_path.write_text(
        f"""<?xml version="1.0"?>
<ECG>
  <RecordingInfo samplingRateHz="500" units="mV" recordId="rec-1"/>
  <Patient patientId="P-99" name="Jane Doe" age="45" sex="F"/>
  <Clinical diagnosis="normal sinus rhythm">
    <Medications><Medication>aspirin</Medication></Medications>
  </Clinical>
  <Leads>
    <Lead name="I">{lead_i}</Lead>
    <Lead name="II">{lead_ii}</Lead>
  </Leads>
  <Annotations>
    <Annotation type="beat" label="N" sampleIndex="50" lead="II"/>
  </Annotations>
</ECG>
""",
        encoding="utf-8",
    )
    return xml_path


def build_dicom_dataset(tmp_path: Path, filename: str = "record.dcm", **extra_tags: str) -> Path:
    """Builds a minimal DICOM ECG Waveform Storage file, optionally with extra top-level tags
    (e.g. StudyDate, StudyTime, AcquisitionDate, AcquisitionTime, AcquisitionDateTime)."""
    from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
    from pydicom.sequence import Sequence
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    dcm_path = tmp_path / filename
    n_samples = 200
    lead_names = ["Lead I", "Lead II", "Lead V1"]
    rng = np.random.default_rng(1)
    raw = rng.integers(-1000, 1000, size=(n_samples, len(lead_names)), dtype=np.int16)

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.9.1.1"
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(dcm_path), {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.PatientID = "PID-77"
    ds.PatientName = "Doe^John"
    ds.PatientSex = "M"
    ds.Manufacturer = "Acme Medical"
    ds.ManufacturerModelName = "CardioScan 3000"
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    for tag, value in extra_tags.items():
        setattr(ds, tag, value)

    waveform_item = Dataset()
    waveform_item.SamplingFrequency = 500.0
    waveform_item.NumberOfWaveformChannels = len(lead_names)
    waveform_item.NumberOfWaveformSamples = n_samples
    waveform_item.WaveformBitsAllocated = 16
    waveform_item.WaveformSampleInterpretation = "SS"
    waveform_item.WaveformData = raw.tobytes()

    channel_defs = []
    for name in lead_names:
        ch = Dataset()
        source_item = Dataset()
        source_item.CodeMeaning = name
        ch.ChannelSourceSequence = Sequence([source_item])
        ch.ChannelSensitivity = "1"
        ch.ChannelSensitivityCorrectionFactor = "1"
        ch.ChannelBaseline = "0"
        unit_item = Dataset()
        unit_item.CodeValue = "mV"
        ch.ChannelSensitivityUnitsSequence = Sequence([unit_item])
        channel_defs.append(ch)
    waveform_item.ChannelDefinitionSequence = Sequence(channel_defs)

    ds.WaveformSequence = Sequence([waveform_item])
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.save_as(str(dcm_path), enforce_file_format=True)
    return dcm_path


@pytest.fixture
def dicom_sample_file(tmp_path: Path) -> Path:
    return build_dicom_dataset(tmp_path)


def _scp_section_header(section_id: int, body: bytes) -> bytes:
    length = 16 + len(body)
    return struct.pack("<HIHBB6s", 0, length, section_id, 1, 1, b"\x00" * 6) + body


def _scp_tlv(tag: int, value: bytes) -> bytes:
    return struct.pack("<BH", tag, len(value)) + value


def _scp_lead_entry(start: int, end: int, lead_id: int) -> bytes:
    return struct.pack("<IIB", start, end, lead_id)


def build_scp_bytes(n_samples: int = 200) -> tuple[bytes, dict[str, np.ndarray], float]:
    """Builds a self-consistent, uncompressed (difference_order=0) SCP-ECG byte stream."""
    section1_body = _scp_tlv(0, b"Doe\x00") + _scp_tlv(1, b"John\x00") + _scp_tlv(2, b"PID-555\x00") + bytes([255])
    section1 = _scp_section_header(1, section1_body)

    section3_body = (
        bytes([3])
        + _scp_lead_entry(0, n_samples, 1)
        + _scp_lead_entry(0, n_samples, 2)
        + _scp_lead_entry(0, n_samples, 3)
    )
    section3 = _scp_section_header(3, section3_body)

    rng = np.random.default_rng(2)
    lead_i = rng.integers(-500, 500, size=n_samples, dtype=np.int16)
    lead_ii = rng.integers(-500, 500, size=n_samples, dtype=np.int16)
    lead_v1 = rng.integers(-500, 500, size=n_samples, dtype=np.int16)

    avm_nanovolts = 1000
    sample_interval_us = 2000
    section6_header = struct.pack("<HHBB", avm_nanovolts, sample_interval_us, 0, 0)

    def encode_lead(samples: np.ndarray) -> bytes:
        raw_bytes = samples.astype("<i2").tobytes()
        return struct.pack("<H", len(raw_bytes)) + raw_bytes

    section6_body = section6_header + encode_lead(lead_i) + encode_lead(lead_ii) + encode_lead(lead_v1)
    section6 = _scp_section_header(6, section6_body)

    header_start = 6
    sections_in_order = [(0, None), (1, section1), (3, section3), (6, section6)]
    num_entries = len(sections_in_order)
    section0_total_len = 16 + num_entries * 10
    cursor = header_start + section0_total_len

    layout = []
    for sec_id, body in sections_in_order:
        if sec_id == 0:
            layout.append((0, section0_total_len, header_start))
        else:
            layout.append((sec_id, len(body), cursor))
            cursor += len(body)

    pointer_body = b"".join(struct.pack("<HII", sid, slen, sidx) for sid, slen, sidx in layout)
    section0 = _scp_section_header(0, pointer_body)

    file_body = section0 + section1 + section3 + section6
    record_length = header_start + len(file_body)
    scp_bytes = struct.pack("<HI", 0, record_length) + file_body

    expected = {"I": lead_i.astype(np.float64) * (avm_nanovolts / 1_000_000.0)}
    return scp_bytes, expected, 1_000_000.0 / sample_interval_us


@pytest.fixture
def scp_sample_file(tmp_path: Path) -> Path:
    scp_bytes, _, _ = build_scp_bytes()
    scp_path = tmp_path / "record.scp"
    scp_path.write_bytes(scp_bytes)
    return scp_path
