"""Unit tests for the Metadata Framework and Validation Framework."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.ecg.constants import CanonicalLead, ECGFormat, ValidationStatus
from app.ecg.models.waveform import LeadSignal, Waveform
from app.ingestion.exceptions import ValidationFailedError
from app.ingestion.metadata_extractor import MetadataOrchestrator
from app.ingestion.parsers.csv.parser import CSVParser
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.ingestion.parsers.wfdb.parser import WFDBParser
from app.ingestion.validator import ValidationOrchestrator


# -- Metadata Framework -------------------------------------------------------------


def test_metadata_orchestrator_extracts_all_categories(wfdb_sample_dir: list[Path]) -> None:
    parsed = WFDBParser().parse(wfdb_sample_dir)
    metadata = MetadataOrchestrator.extract(parsed, record_id="rec-1")

    assert metadata.patient.age == 81
    assert metadata.patient.sex == "male"
    assert metadata.ecg.record_id == "rec-1"
    assert metadata.ecg.lead_count == 15
    assert metadata.ecg.xyz_available is True
    assert metadata.clinical.reason_for_examination == "Myocardial infarction"
    assert metadata.device.manufacturer is None
    assert metadata.quality.is_empty()


def test_patient_metadata_extractor_never_fabricates_missing_fields(csv_sample_file: Path) -> None:
    parsed = CSVParser().parse([csv_sample_file])
    metadata = MetadataOrchestrator.extract(parsed, record_id="rec-2")
    # csv_sample_file only supplies patient_id -- everything else stays unset.
    assert metadata.patient.patient_id == "PT-001"
    assert metadata.patient.name is None
    assert metadata.patient.date_of_birth is None


# -- Validation Framework -------------------------------------------------------------


def test_validation_passes_with_warning_for_incomplete_patient_metadata(wfdb_sample_dir: list[Path]) -> None:
    parsed = WFDBParser().parse(wfdb_sample_dir)
    metadata = MetadataOrchestrator.extract(parsed, record_id="rec-3")
    validated = ValidationOrchestrator.validate(parsed, metadata)

    assert validated.validation_result.status == ValidationStatus.WARNING
    assert validated.validation_result.is_valid
    assert any(issue.validator_name == "PatientMetadataValidator" for issue in validated.validation_result.issues)


def test_validation_fails_and_raises_when_source_files_missing() -> None:
    waveform = Waveform(leads={CanonicalLead.I: LeadSignal(CanonicalLead.I, np.zeros(10))}, sampling_rate_hz=100)
    parsed = ParsedECG(source_format=ECGFormat.CSV, source_files=(), parser_name="CSVParser", waveform=waveform)
    metadata = MetadataOrchestrator.extract(parsed, record_id="rec-4")

    with pytest.raises(ValidationFailedError) as exc_info:
        ValidationOrchestrator.validate(parsed, metadata)

    assert exc_info.value.validation_result.status == ValidationStatus.FAIL
    assert any(issue.validator_name == "MissingFilesValidator" for issue in exc_info.value.validation_result.issues)


def test_validation_never_modifies_parsed_ecg(wfdb_sample_dir: list[Path]) -> None:
    parsed = WFDBParser().parse(wfdb_sample_dir)
    metadata = MetadataOrchestrator.extract(parsed, record_id="rec-5")
    original_sample_count = parsed.waveform.sample_count

    ValidationOrchestrator.validate(parsed, metadata)

    assert parsed.waveform.sample_count == original_sample_count


def test_validation_is_deterministic(wfdb_sample_dir: list[Path]) -> None:
    parsed = WFDBParser().parse(wfdb_sample_dir)
    metadata = MetadataOrchestrator.extract(parsed, record_id="rec-6")

    result_a = ValidationOrchestrator.validate(parsed, metadata)
    result_b = ValidationOrchestrator.validate(parsed, metadata)

    assert result_a.validation_result.status == result_b.validation_result.status
    assert len(result_a.validation_result.issues) == len(result_b.validation_result.issues)
