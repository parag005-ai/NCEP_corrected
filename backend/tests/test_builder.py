"""Unit tests for the ECGRecord Builder."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.ecg.constants import CanonicalLead, ECGFormat, ValidationStatus
from app.ecg.models.waveform import LeadSignal, Waveform
from app.ingestion.builders.ecg_record_builder import ECGRecordBuilder
from app.ingestion.exceptions import BuilderError
from app.ingestion.metadata_extractor import MetadataOrchestrator
from app.ingestion.parsers.wfdb.parser import WFDBParser
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.validation.validation_result import ValidatedParsedECG, ValidationResult
from app.ingestion.validator import ValidationOrchestrator


def test_builder_happy_path(wfdb_sample_dir: list[Path]) -> None:
    parsed = WFDBParser().parse(wfdb_sample_dir)
    metadata = MetadataOrchestrator.extract(parsed, record_id="rec-1")
    validated = ValidationOrchestrator.validate(parsed, metadata)

    record = ECGRecordBuilder.build(validated, upload_id="upload-1")

    assert record.record_id == "rec-1"
    assert record.source_information.upload_id == "upload-1"
    assert record.source_information.parser_name == "WFDBParser"
    assert set(record.source_information.original_filenames) == {"ptbsample.hea", "ptbsample.dat"}
    # Waveform samples are passed through unmodified (Builder Rule 13.9.2).
    assert record.waveform.leads.keys() == parsed.waveform.leads.keys()
    for lead in record.waveform.leads:
        assert np.array_equal(record.waveform.leads[lead].samples, parsed.waveform.leads[lead].samples)


def test_builder_rejects_failed_validation() -> None:
    waveform = Waveform(leads={CanonicalLead.I: LeadSignal(CanonicalLead.I, np.zeros(10))}, sampling_rate_hz=100)
    parsed = ParsedECG(source_format=ECGFormat.CSV, source_files=(Path("x.csv"),), parser_name="CSVParser", waveform=waveform)
    metadata = MetadataOrchestrator.extract(parsed, record_id="rec-2")

    fake_failed_result = ValidatedParsedECG(
        parsed=parsed,
        metadata=metadata,
        validation_result=ValidationResult(status=ValidationStatus.FAIL, issues=()),
    )

    with pytest.raises(BuilderError):
        ECGRecordBuilder.build(fake_failed_result, upload_id="upload-2")


def test_builder_produces_exactly_one_record_per_parsed_ecg(wfdb_sample_dir: list[Path]) -> None:
    parsed = WFDBParser().parse(wfdb_sample_dir)
    metadata = MetadataOrchestrator.extract(parsed, record_id="rec-3")
    validated = ValidationOrchestrator.validate(parsed, metadata)

    record_a = ECGRecordBuilder.build(validated, upload_id="upload-3")
    record_b = ECGRecordBuilder.build(validated, upload_id="upload-3")

    assert record_a.record_id == record_b.record_id == "rec-3"
