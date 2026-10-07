"""Shared ECG enumerations and constants used across the NCEP platform.

These are the vocabulary every ingestion module (parsers, metadata
extractors, validators, the builder) shares. No business logic belongs
here -- only names.
"""

from __future__ import annotations

from enum import Enum


class ECGFormat(str, Enum):
    """Source ECG formats supported by Phase 1 (Implementation Spec 1.7 / 10.3)."""

    WFDB = "WFDB"
    XML = "XML"
    DICOM = "DICOM"
    SCP_ECG = "SCP_ECG"
    CSV = "CSV"


SUPPORTED_FORMATS: tuple[ECGFormat, ...] = tuple(ECGFormat)


class CanonicalLead(str, Enum):
    """The 15 canonical NCEP lead slots (Implementation Spec Chapter 9.3).

    12 standard clinical leads plus the 3 Frank orthogonal leads. A
    recording is never required to populate all 15 -- only the leads
    actually present in the source are populated (9.4).
    """

    I = "I"  # noqa: E741 -- this is the ECG lead name "I", not a loop variable
    II = "II"
    III = "III"
    aVR = "aVR"
    aVL = "aVL"
    aVF = "aVF"
    V1 = "V1"
    V2 = "V2"
    V3 = "V3"
    V4 = "V4"
    V5 = "V5"
    V6 = "V6"
    X = "X"
    Y = "Y"
    Z = "Z"


STANDARD_LIMB_LEADS: tuple[CanonicalLead, ...] = (CanonicalLead.I, CanonicalLead.II, CanonicalLead.III)

AUGMENTED_LIMB_LEADS: tuple[CanonicalLead, ...] = (CanonicalLead.aVR, CanonicalLead.aVL, CanonicalLead.aVF)

PRECORDIAL_LEADS: tuple[CanonicalLead, ...] = (
    CanonicalLead.V1,
    CanonicalLead.V2,
    CanonicalLead.V3,
    CanonicalLead.V4,
    CanonicalLead.V5,
    CanonicalLead.V6,
)

STANDARD_12_LEADS: tuple[CanonicalLead, ...] = STANDARD_LIMB_LEADS + AUGMENTED_LIMB_LEADS + PRECORDIAL_LEADS

FRANK_ORTHOGONAL_LEADS: tuple[CanonicalLead, ...] = (CanonicalLead.X, CanonicalLead.Y, CanonicalLead.Z)

CANONICAL_LEAD_ORDER: tuple[CanonicalLead, ...] = STANDARD_12_LEADS + FRANK_ORTHOGONAL_LEADS
"""The full 15-lead canonical ordering. Waveform never contains leads outside this set."""


class ValidationSeverity(str, Enum):
    """Severity of an individual validation finding (Implementation Spec Chapter 6.6 / doc1)."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class ValidationStatus(str, Enum):
    """Outcome of a single validator or the aggregate ValidationResult (Chapter 11.12)."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class ProcessingState(str, Enum):
    """ECG lifecycle states (Implementation Spec Chapter 6)."""

    UPLOADED = "UPLOADED"
    FORMAT_DETECTED = "FORMAT_DETECTED"
    PARSING = "PARSING"
    PARSED = "PARSED"
    METADATA_EXTRACTED = "METADATA_EXTRACTED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    STANDARDIZING = "STANDARDIZING"
    STANDARDIZED = "STANDARDIZED"
    STORED = "STORED"
    READY_FOR_PREPROCESSING = "READY_FOR_PREPROCESSING"
    FAILED_FORMAT_DETECTION = "FAILED_FORMAT_DETECTION"
    FAILED_PARSING = "FAILED_PARSING"
    FAILED_METADATA_EXTRACTION = "FAILED_METADATA_EXTRACTION"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_STORAGE = "FAILED_STORAGE"


DEFAULT_ENCODING = "utf-8"
API_VERSION = "v1"
MAX_UPLOAD_SIZE_BYTES = 200 * 1024 * 1024  # 200 MiB per upload session

DEFAULT_SIGNAL_UNITS = "mV"

# WFDB companion file extensions recognized by the WFDB parser (Implementation
# Spec "WFDB Support"). Non-exhaustive -- any other extension referenced by
# the header's segment/signal specifications is still honored.
WFDB_HEADER_EXT = ".hea"
WFDB_ANNOTATION_EXTS: tuple[str, ...] = (".atr", ".qrs", ".ecg")
WFDB_XYZ_HINT_EXTS: tuple[str, ...] = (".xyz",)
