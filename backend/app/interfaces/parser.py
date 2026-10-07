from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from app.ecg.constants import ECGFormat
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG


class ParserInterface(ABC):
    """Contract for format-agnostic ECG ingestion parsers (Implementation Spec Chapter 10).

    Every parser reads only its source format, never validates, never
    preprocesses, and produces exactly one ParsedECG per recording.
    """

    format: ClassVar[ECGFormat]

    @abstractmethod
    def can_parse(self, files: Sequence[Path]) -> bool:
        """Return whether this parser can handle the given set of uploaded files."""

    @abstractmethod
    def parse(self, files: Sequence[Path]) -> ParsedECG:
        """Parse the uploaded recording and return a ParsedECG."""
