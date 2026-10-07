"""The Summary Report delivery contract.

The Summary Report's presentation belongs to the NCEP frontend, so the backend
delivers the composed document as structured data rather than as a rendered
page. This module is the single definition of that contract: it projects the
``ReportDocument`` the builders produced into the JSON persisted as a report
artifact and later served to the client.

The projection is deliberately lossless in the ways a reader depends on --
section order, section identity, every value with its availability and
placeholder, notes, figure references and traceability metadata -- and
deliberately lossy about everything internal. No storage location, relative
path or absolute path is ever written: a client reaches a figure through the
report's registered artifacts, by type.

Keys are camelCase, matching every other NCEP response.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

from app.reporting.builders.sections import (
    ReportDocument,
    ReportFigure,
    ReportSection,
    ReportValue,
)

#: Version of this contract. Bumped when the shape below changes, so a client
#: can tell a historical Summary from a current one -- persisted documents are
#: immutable and are served exactly as they were written.
SUMMARY_CONTRACT_VERSION = "1.0.0"


def _plain(value: Any) -> Any:
    """Converts frozen context structures back into JSON-serializable values."""
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_plain(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _value_to_dict(value: ReportValue) -> dict:
    return {
        "label": value.label,
        "value": value.value,
        "unit": value.unit,
        "reference": value.reference,
        "availability": value.availability.value,
        "placeholder": value.placeholder,
        # What a client shows: the value, or its standardized placeholder.
        "displayValue": value.display_value,
        "isAvailable": value.is_available,
    }


def _figure_to_dict(figure: ReportFigure) -> dict:
    """A figure by identity, never by location.

    The bytes are fetched through the report's registered artifacts; the
    ``artifactType`` is what ties this reference to one of them.
    """
    return {
        "caption": figure.caption,
        "artifactType": figure.artifact_type.value,
        "mediaType": figure.media_type,
        "figureMetadata": _plain(figure.figure_metadata),
    }


def _section_to_dict(section: ReportSection) -> dict:
    return {
        "id": section.id.value,
        "title": section.title,
        "availability": section.availability.value,
        "placeholder": section.placeholder,
        "displayPlaceholder": section.display_placeholder,
        "isAvailable": section.is_available,
        "values": [_value_to_dict(value) for value in section.values],
        "notes": list(section.notes),
        "figures": [_figure_to_dict(figure) for figure in section.figures],
    }


def document_to_dict(document: ReportDocument, *, report_id: str) -> dict:
    """Projects a composed report document into its delivery contract.

    ``report_id`` is supplied by the caller because a document is composed
    before the report version it belongs to exists; binding it here is what
    ties a persisted Summary to exactly one ``GeneratedReport``.
    """
    metadata = document.metadata
    return {
        "contractVersion": SUMMARY_CONTRACT_VERSION,
        "reportId": report_id,
        "reportType": document.report_type.value,
        "title": document.title,
        "generation": {
            "ecgRecordId": metadata.ecg_record_id,
            "jobId": metadata.job_id,
            "reportVersion": metadata.report_version,
            "generatedAt": metadata.generated_at.isoformat(),
            "pipelineVersion": metadata.pipeline_version,
            "schemaVersion": metadata.schema_version,
            "softwareVersion": metadata.software_version,
        },
        "sections": [_section_to_dict(section) for section in document.sections],
    }
