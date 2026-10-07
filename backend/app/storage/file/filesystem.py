"""Filesystem Storage Adapter.

Purpose:
    Persist ingestion artifacts (original files, waveform, metadata,
    manifest) to a record-scoped directory tree (Implementation Spec
    15.10). This is the Phase 1 storage backend for waveform and JSON
    artifacts; structured metadata may additionally be persisted to
    PostgreSQL by a future repository implementation without changing
    callers (Repository Pattern, 15.14 Principle 3).

Responsibilities:
    - Organize artifacts by record_id, not by original upload structure.
    - Preserve original uploaded files read-only (Business Rule 8.4).
    - Write/read JSON and binary artifacts.
    - Roll back (delete) a record's directory tree if a storage operation
      does not complete successfully (Implementation Spec 15.8 -- atomic
      storage; used by StorageOrchestrator.store's rollback path).

Shall NOT:
    - Parse ECG content.
    - Modify the original uploaded files.

Layout:
    <root>/<record_id>/
        raw/                  original uploaded files (copied, read-only)
        waveform/waveform.npz + waveform.csv + waveform_meta.json
        metadata/*.json       one file per metadata category + annotations
        manifest/manifest.json
"""

from __future__ import annotations

import json
import hashlib
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.ingestion.exceptions import FileStorageError
from app.storage import cloudinary_backup

# Read-only for everyone (no write bits). Applied to preserved raw uploads
# so accidental modification after storage fails loudly instead of silently
# corrupting the original recording (Business Rule 8.4).
_READ_ONLY_MODE = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH

#: Cloudinary public_id prefix for every artifact this store backs up.
_CLOUDINARY_PREFIX = "ecg_storage"


class FilesystemArtifactStore:
    """Persists ingestion artifacts under a record-scoped directory tree.

    Every write is backed up to Cloudinary (best-effort) so the record
    survives a host that wipes local disk between requests; every read falls
    back to that backup only when the local copy is already gone. See
    app/storage/cloudinary_backup.py.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        settings = get_settings()
        self._root = Path(root) if root is not None else Path(settings.ecg_storage_root)
        # Explicit test roots are isolated filesystem stores. Production's
        # default ``auto`` resolves to Cloudinary and makes every write hard-
        # fail if the durable object write cannot be confirmed.
        self._durable_mode = "filesystem" if root is not None else settings.resolved_ecg_durable_storage_mode

    def record_dir(self, record_id: str) -> Path:
        return self._root / record_id

    def _cloudinary_id(self, record_id: str, relative_path: str) -> str:
        return f"{_CLOUDINARY_PREFIX}/{record_id}/{relative_path}"

    def write_bytes(self, record_id: str, relative_path: str, data: bytes) -> Path:
        path = self.record_dir(record_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(data)
        except OSError as exc:
            raise FileStorageError(f"Failed to write artifact {relative_path!r} for record {record_id}: {exc}") from exc
        try:
            cloudinary_backup.upload(
                self._cloudinary_id(record_id, relative_path),
                data,
                required=self._durable_mode == "cloudinary",
            )
        except Exception as exc:
            raise FileStorageError(
                f"Failed to durably store artifact {relative_path!r} for record {record_id}"
            ) from exc
        return path

    def write_json(self, record_id: str, relative_path: str, data: dict) -> Path:
        return self.write_bytes(record_id, relative_path, json.dumps(data, indent=2, default=str).encode("utf-8"))

    def copy_raw_file(self, record_id: str, source: Path) -> Path:
        destination = self.record_dir(record_id) / "raw" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, destination)
            destination.chmod(_READ_ONLY_MODE)
        except OSError as exc:
            raise FileStorageError(
                f"Failed to preserve original file {source.name!r} for record {record_id}: {exc}"
            ) from exc
        try:
            cloudinary_backup.upload(
                self._cloudinary_id(record_id, f"raw/{source.name}"),
                destination.read_bytes(),
                required=self._durable_mode == "cloudinary",
            )
        except Exception as exc:
            raise FileStorageError(
                f"Failed to durably store original file {source.name!r} for record {record_id}"
            ) from exc
        return destination

    def read_bytes(self, record_id: str, relative_path: str) -> bytes:
        path = self.record_dir(record_id) / relative_path
        try:
            return path.read_bytes()
        except OSError:
            pass  # Fall through to the Cloudinary backup below.

        try:
            data = cloudinary_backup.download(self._cloudinary_id(record_id, relative_path))
        except Exception as exc:  # noqa: BLE001 -- surfaced as the same error either source would raise
            raise FileStorageError(f"Failed to read artifact {relative_path!r} for record {record_id}: {exc}") from exc

        try:  # Re-populate the local cache so later reads in this process hit disk again.
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except OSError:
            pass  # The read itself still succeeds even if re-caching doesn't.
        return data

    def read_json(self, record_id: str, relative_path: str) -> dict:
        return json.loads(self.read_bytes(record_id, relative_path).decode("utf-8"))

    def exists(self, record_id: str) -> bool:
        return self.record_dir(record_id).exists()

    def materialize(self, record_id: str, relative_path: str) -> Path:
        """Returns a readable local cache path, restoring the exact object if needed."""
        path = self.record_dir(record_id) / relative_path
        if path.is_file():
            return path
        self.read_bytes(record_id, relative_path)
        if not path.is_file():
            raise FileStorageError(f"Artifact {relative_path!r} for record {record_id} could not be cached")
        return path

    def finalize_artifact_manifest(self, record_id: str, required_paths: list[str]) -> dict:
        """Records and verifies every artifact required for canonical success."""
        artifacts: list[dict] = []
        for relative_path in sorted(set(required_paths)):
            local_path = self.materialize(record_id, relative_path)
            local_data = local_path.read_bytes()
            if self._durable_mode == "cloudinary":
                durable_data = cloudinary_backup.download(self._cloudinary_id(record_id, relative_path))
                if durable_data != local_data:
                    raise FileStorageError(
                        f"Durable artifact checksum mismatch for {relative_path!r} in record {record_id}"
                    )
            artifacts.append(
                {
                    "relativePath": relative_path,
                    "sizeBytes": len(local_data),
                    "checksumSha256": hashlib.sha256(local_data).hexdigest(),
                    "mandatory": True,
                    "durableReference": (
                        self._cloudinary_id(record_id, relative_path)
                        if self._durable_mode == "cloudinary"
                        else str(local_path)
                    ),
                }
            )
        manifest = {
            "schemaVersion": "1.0",
            "recordId": record_id,
            "durableStorageMode": self._durable_mode,
            "verifiedAt": datetime.now(timezone.utc).isoformat(),
            "artifacts": artifacts,
        }
        manifest_path = "manifest/artifact_manifest.json"
        self.write_json(record_id, manifest_path, manifest)
        if self._durable_mode == "cloudinary":
            durable_manifest = cloudinary_backup.download(self._cloudinary_id(record_id, manifest_path))
            if json.loads(durable_manifest.decode("utf-8")) != manifest:
                raise FileStorageError(f"Durable artifact manifest could not be verified for record {record_id}")
        return manifest

    def verify_artifact_manifest(self, record_id: str, manifest: dict) -> None:
        """Checks that every mandatory manifest entry is readable and unmodified."""
        for artifact in manifest.get("artifacts", []):
            if not artifact.get("mandatory"):
                continue
            relative_path = artifact.get("relativePath")
            expected = artifact.get("checksumSha256")
            if not relative_path or not expected:
                raise FileStorageError(f"Invalid artifact manifest entry for record {record_id}")
            data = self.read_bytes(record_id, relative_path)
            if hashlib.sha256(data).hexdigest() != expected:
                raise FileStorageError(
                    f"Artifact checksum mismatch for {relative_path!r} in record {record_id}"
                )

    def hydrate(self, record_id: str) -> None:
        """Re-populates this record's local directory from the Cloudinary
        backup when local disk has lost it entirely (e.g. a host that wipes
        disk between deploys/restarts, as opposed to the per-file cache-miss
        `read_bytes` already handles). No-op if the local directory already
        exists or nothing is backed up. Best-effort: a caller that still
        finds artifacts missing afterwards raises its own "unavailable"
        error, same as if this were never called.
        """
        if self.record_dir(record_id).is_dir():
            return
        prefix = f"{_CLOUDINARY_PREFIX}/{record_id}/"
        for public_id in cloudinary_backup.list_prefix(prefix):
            relative_path = public_id[len(prefix) :]
            try:
                data = cloudinary_backup.download(public_id)
            except Exception:  # noqa: BLE001 -- one bad artifact shouldn't block restoring the rest
                continue
            path = self.record_dir(record_id) / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def remove_record(self, record_id: str) -> None:
        """Deletes every artifact written for a record (storage rollback).

        Raw files are stored read-only, so write permission is restored
        before removal -- otherwise deletion fails on platforms (e.g.
        Windows) that reject removing a read-only file outright.
        """
        path = self.record_dir(record_id)
        if path.exists():
            for child in path.rglob("*"):
                if child.is_file():
                    try:
                        child.chmod(stat.S_IWRITE | stat.S_IREAD)
                    except OSError:
                        pass
            shutil.rmtree(path, ignore_errors=True)
        cloudinary_backup.delete_prefix(f"{_CLOUDINARY_PREFIX}/{record_id}")
