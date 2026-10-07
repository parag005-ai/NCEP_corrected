"""Value objects describing the canonical ECG artifacts of one recording.

These live in the model layer because they are shared by two layers above it:
``ECGArtifactRepository`` produces them, and the Generation Context carries
them. Keeping them here keeps the dependency direction one-way -- context and
repositories both depend on models, never on each other.

Sprint 2.10 lists the raw waveform, metadata, manifest and preprocessing
outputs as the ECG artifacts of the Generation Context.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.reporting.models.documents import freeze_document


@dataclass(frozen=True)
class ECGArtifactRef:
    """Location and size of one stored ECG artifact.

    Waveform samples are referenced, never loaded into the Generation Context:
    reading them is the Visualization Engine's Waveform Reader responsibility
    (Sprint 4.5), and a report must not carry a whole recording in memory.
    """

    relative_path: str
    absolute_path: str
    size_bytes: int


@dataclass(frozen=True)
class ECGArtifactBundle:
    """The canonical ECG artifacts available for one recording.

    Small documents (waveform descriptor, metadata categories, manifest,
    preprocessing report) are read eagerly so no downstream stage has to touch
    the artifact store during composition (Sprint 6.5). Large binary artifacts
    are referenced by path.
    """

    record_dir: str
    waveform: ECGArtifactRef
    waveform_descriptor: Mapping[str, Any]
    metadata_documents: Mapping[str, Mapping[str, Any]]
    waveform_csv: ECGArtifactRef | None = None
    manifest: Mapping[str, Any] | None = None
    preprocessing_signal: ECGArtifactRef | None = None
    preprocessing_report: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "waveform_descriptor", freeze_document(self.waveform_descriptor))
        object.__setattr__(self, "metadata_documents", freeze_document(self.metadata_documents))
        if self.manifest is not None:
            object.__setattr__(self, "manifest", freeze_document(self.manifest))
        if self.preprocessing_report is not None:
            object.__setattr__(self, "preprocessing_report", freeze_document(self.preprocessing_report))
