"""Tests for the artifact lifecycle and integrity verification (Sprint 9.8 / 9.11)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.reporting.constants import ArtifactStatus, ArtifactType
from app.reporting.exceptions import InvalidArtifactTransitionError
from app.reporting.repositories import ReportArtifactRepository
from app.reporting.storage import (
    ALLOWED_ARTIFACT_TRANSITIONS,
    LIFECYCLE_ORDER,
    ArtifactIntegrityVerifier,
    ArtifactLifecycle,
)

from tests.reporting.test_repositories import make_report


# ---------------------------------------------------------------------------
# Lifecycle (Sprint 9.8)
# ---------------------------------------------------------------------------


def test_the_lifecycle_follows_the_declared_order():
    assert LIFECYCLE_ORDER == (
        ArtifactStatus.GENERATED,
        ArtifactStatus.REGISTERED,
        ArtifactStatus.VALIDATED,
        ArtifactStatus.STORED,
        ArtifactStatus.AVAILABLE,
        ArtifactStatus.ARCHIVED,
    )
    assert set(ALLOWED_ARTIFACT_TRANSITIONS) == set(ArtifactStatus)


def test_an_artifact_advances_one_step_at_a_time():
    assert ArtifactLifecycle.can_transition(ArtifactStatus.REGISTERED, ArtifactStatus.VALIDATED)
    assert not ArtifactLifecycle.can_transition(ArtifactStatus.REGISTERED, ArtifactStatus.AVAILABLE)

    with pytest.raises(InvalidArtifactTransitionError, match="REGISTERED to AVAILABLE"):
        ArtifactLifecycle.validate(ArtifactStatus.REGISTERED, ArtifactStatus.AVAILABLE)


def test_an_archived_artifact_is_final():
    assert ArtifactLifecycle.is_final(ArtifactStatus.ARCHIVED)
    assert not ArtifactLifecycle.is_final(ArtifactStatus.AVAILABLE)


def test_the_path_between_states_walks_every_step():
    path = ArtifactLifecycle.path(ArtifactStatus.REGISTERED, ArtifactStatus.AVAILABLE)

    assert path == (ArtifactStatus.VALIDATED, ArtifactStatus.STORED, ArtifactStatus.AVAILABLE)
    assert ArtifactLifecycle.path(ArtifactStatus.AVAILABLE, ArtifactStatus.AVAILABLE) == ()


def test_an_artifact_never_moves_backwards():
    with pytest.raises(InvalidArtifactTransitionError, match="backwards"):
        ArtifactLifecycle.path(ArtifactStatus.AVAILABLE, ArtifactStatus.REGISTERED)


# ---------------------------------------------------------------------------
# Integrity verification (Sprint 9.11)
# ---------------------------------------------------------------------------


@pytest.fixture
def verified_artifact(session, upstream, tmp_path):
    """A report whose single artifact is genuinely on disk."""
    report = make_report(session, upstream)
    report.storage_dir = str(tmp_path)
    data = b"<html>report</html>"
    path = tmp_path / "documents" / "detailed_report.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    artifact = ReportArtifactRepository(session).register(
        report=report,
        artifact_type=ArtifactType.DETAILED_HTML,
        content_type="text/html; charset=utf-8",
        storage_location="documents/detailed_report.html",
        file_size_bytes=len(data),
        checksum_sha256=hashlib.sha256(data).hexdigest(),
    )
    session.flush()
    return report, artifact, path


def test_an_intact_artifact_verifies(verified_artifact):
    report, artifact, _ = verified_artifact

    result = ArtifactIntegrityVerifier().verify(report, artifact)

    assert result.verified
    assert result.reason is None
    assert result.artifact_id == artifact.id


def test_a_missing_file_fails_verification(verified_artifact):
    report, artifact, path = verified_artifact
    path.unlink()

    result = ArtifactIntegrityVerifier().verify(report, artifact)

    assert not result.verified
    assert "missing" in result.reason


def test_a_truncated_file_fails_verification(verified_artifact):
    report, artifact, path = verified_artifact
    path.write_bytes(b"<html>")

    result = ArtifactIntegrityVerifier().verify(report, artifact)

    assert not result.verified
    assert "bytes but the registry records" in result.reason


def test_a_tampered_file_fails_verification(verified_artifact):
    report, artifact, path = verified_artifact
    original = path.read_bytes()
    path.write_bytes(b"<html>tampered!!</html>"[: len(original)].ljust(len(original), b" "))

    result = ArtifactIntegrityVerifier().verify(report, artifact)

    assert not result.verified
    assert "checksum" in result.reason


def test_verification_resolves_artifacts_inside_the_report_directory(verified_artifact):
    report, artifact, path = verified_artifact

    assert ArtifactIntegrityVerifier().resolve(report, artifact) == Path(path)


def test_every_artifact_of_a_report_is_verified(session, verified_artifact):
    report, artifact, _ = verified_artifact
    artifacts = ReportArtifactRepository(session).list_for_report(report.id)

    results = ArtifactIntegrityVerifier().verify_all(report, artifacts)

    assert [result.artifact_id for result in results] == [artifact.id]
    assert all(result.verified for result in results)
