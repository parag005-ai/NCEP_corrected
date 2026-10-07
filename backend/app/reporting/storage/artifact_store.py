"""Filesystem storage for generated report artifacts (Sprint 4.2 / 9.10).

Holds the *bytes* of everything a report generation produces -- ECG SVGs
today, HTML and PDF documents once those stages exist. The registry entry that
describes each file is a ``ReportArtifact`` row; this store deliberately knows
nothing about it, so the storage backend can change without touching the
registry (Sprint 9.10).

Layout:
    <root>/<ecg_record_id>/<job_id>/<relative_path>

Artifacts are scoped by generation job rather than by report version, because
a stage writes its output before the report version it will belong to exists
(the report row is created by the composition stage). The job directory is the
report version's storage location once that row is created.

Every write returns the size and SHA-256 checksum of what was actually stored,
so integrity metadata is measured rather than asserted (Sprint 9.11).
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.reporting.exceptions import ReportArtifactStorageError
from app.storage import cloudinary_backup

#: Cloudinary public_id prefix for every artifact this store backs up.
_CLOUDINARY_PREFIX = "report_storage"


@dataclass(frozen=True)
class StoredArtifact:
    """Where an artifact was written and what was written there."""

    relative_path: str
    absolute_path: str
    file_size_bytes: int
    checksum_sha256: str


class ReportArtifactStore:
    """Persists generated report artifacts under a job-scoped directory tree.

    Every write is backed up to Cloudinary (best-effort) so a report survives
    a host that wipes local disk between requests; every read falls back to
    that backup only when the local copy is already gone. See
    app/storage/cloudinary_backup.py.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(root) if root is not None else Path(get_settings().report_storage_root)

    def job_dir(self, ecg_record_id: str, job_id: str) -> Path:
        """The directory holding every artifact produced by one generation job."""
        return self._root / ecg_record_id / job_id

    def _cloudinary_id(self, path: Path) -> str | None:
        """The backup public_id for a path under this store's root, or None if it isn't."""
        try:
            relative = path.relative_to(self._root)
        except ValueError:
            return None
        return f"{_CLOUDINARY_PREFIX}/{relative}"

    def write(
        self,
        *,
        ecg_record_id: str,
        job_id: str,
        relative_path: str,
        data: bytes,
    ) -> StoredArtifact:
        """Writes one artifact and reports its measured size and checksum.

        Raises:
            ReportArtifactStorageError: the artifact could not be written.
        """
        path = self.job_dir(ecg_record_id, job_id) / relative_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except OSError as exc:
            raise ReportArtifactStorageError(
                f"Failed to store report artifact {relative_path!r} for job {job_id!r}: {exc}"
            ) from exc

        public_id = self._cloudinary_id(path)
        if public_id is not None:
            cloudinary_backup.upload(public_id, data)

        return StoredArtifact(
            relative_path=relative_path,
            absolute_path=str(path),
            file_size_bytes=path.stat().st_size,
            checksum_sha256=hashlib.sha256(data).hexdigest(),
        )

    def read(self, absolute_path: str | Path) -> bytes:
        """Reads a stored artifact back, falling back to its Cloudinary backup
        if the local copy is gone (see module docstring).

        Raises:
            ReportArtifactStorageError: the artifact could not be read from
                either source.
        """
        path = Path(absolute_path)
        try:
            return path.read_bytes()
        except OSError as exc:
            public_id = self._cloudinary_id(path)
            if public_id is None:
                raise ReportArtifactStorageError(f"Failed to read report artifact at {path}: {exc}") from exc

        try:
            data = cloudinary_backup.download(public_id)
        except Exception as backup_exc:  # noqa: BLE001 -- surfaced as the same error either source would raise
            raise ReportArtifactStorageError(
                f"Failed to read report artifact at {path}: {backup_exc}"
            ) from backup_exc

        try:  # Re-populate the local cache so later reads in this process hit disk again.
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except OSError:
            pass  # The read itself still succeeds even if re-caching doesn't.
        return data

    def copy(
        self,
        *,
        source_path: str | Path,
        ecg_record_id: str,
        job_id: str,
        relative_path: str,
    ) -> StoredArtifact:
        """Copies an existing artifact into another job's directory.

        Used when a deterministic artifact is reused across report versions:
        the bytes are carried over rather than regenerated, and the copy is
        re-measured so its recorded size and checksum describe the file that
        actually exists (Sprint 4.21).
        """
        return self.write(
            ecg_record_id=ecg_record_id,
            job_id=job_id,
            relative_path=relative_path,
            data=self.read(source_path),
        )

    def remove_job(self, ecg_record_id: str, job_id: str) -> None:
        """Deletes every artifact one generation job produced (rollback on failure)."""
        path = self.job_dir(ecg_record_id, job_id)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        cloudinary_backup.delete_prefix(f"{_CLOUDINARY_PREFIX}/{ecg_record_id}/{job_id}")
