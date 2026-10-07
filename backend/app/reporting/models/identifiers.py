"""Identifier generation for reporting entities.

Every reporting entity carries a short, human-recognisable, prefixed opaque
identifier. Prefixes make identifiers self-describing in logs, audit records
and API responses, and keep them distinguishable from the upstream
``ecg-``/``rpt-`` identifiers already in use.
"""

from __future__ import annotations

import uuid

JOB_ID_PREFIX = "rgj"
REPORT_ID_PREFIX = "grp"
ARTIFACT_ID_PREFIX = "rart"

_RANDOM_SUFFIX_LENGTH = 12


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:_RANDOM_SUFFIX_LENGTH]}"


def new_job_id() -> str:
    """Identifier for a ReportGenerationJob."""
    return _new_id(JOB_ID_PREFIX)


def new_report_id() -> str:
    """Identifier for a GeneratedReport."""
    return _new_id(REPORT_ID_PREFIX)


def new_artifact_id() -> str:
    """Identifier for a ReportArtifact."""
    return _new_id(ARTIFACT_ID_PREFIX)
