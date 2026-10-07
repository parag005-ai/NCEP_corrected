"""Tests for the immutability and placeholder behaviour of the Generation Context."""

from __future__ import annotations

import dataclasses

import pytest

from app.reporting.constants import PLACEHOLDER_AWAITING_SIGNAL_PROCESSING, SectionStatus
from app.reporting.context import ContextSection, SignalProcessingOutputs
from app.reporting.models import freeze_document


def test_documents_are_deep_frozen():
    frozen = freeze_document({"leads": ["I", "II"], "quality": {"score": 0.9}})

    assert frozen["leads"] == ("I", "II")
    with pytest.raises(TypeError):
        frozen["leads"] = ()
    with pytest.raises(TypeError):
        frozen["quality"]["score"] = 0.1


def test_context_sections_are_frozen():
    section = ContextSection.awaiting_signal_processing("ECG Parameters")

    with pytest.raises(dataclasses.FrozenInstanceError):
        section.status = SectionStatus.AVAILABLE


def test_phase_one_signal_processing_sections_are_explicit_placeholders():
    outputs = SignalProcessingOutputs.awaiting_signal_processing()

    assert len(outputs.sections) == 6
    assert not outputs.is_available
    for section in outputs.sections:
        assert section.status is SectionStatus.AWAITING_SIGNAL_PROCESSING
        assert section.placeholder == PLACEHOLDER_AWAITING_SIGNAL_PROCESSING
        assert section.payload is None
        assert not section.is_available


def test_a_section_carries_a_read_only_payload_once_its_source_is_connected():
    """The Phase 2 extension point: the same section gains a payload, unchanged in shape."""
    section = ContextSection(
        name="ECG Parameters",
        status=SectionStatus.AVAILABLE,
        payload={"heart_rate_bpm": 78, "intervals": {"pr_ms": 162}},
    )

    assert section.is_available
    assert section.payload["heart_rate_bpm"] == 78
    with pytest.raises(TypeError):
        section.payload["intervals"]["pr_ms"] = 0
