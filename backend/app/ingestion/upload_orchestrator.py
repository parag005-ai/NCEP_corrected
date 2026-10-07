"""Upload Orchestrator (Upload Layer).

Purpose:
    Receive ECG files from the API layer, create a temporary Upload
    Session, and preserve the original files (Implementation Spec 3.3).

Responsibilities:
    - Receive uploaded file contents.
    - Reject uploads that exceed the configured size limit or contain
      duplicate filenames (Business Rule: an upload must unambiguously
      represent exactly one recording).
    - Persist them to a temporary, upload-scoped directory.
    - Assign an upload identifier and timestamp.
    - Remove the temporary upload directory once the caller is done with it
      (`cleanup_session`), whether processing succeeded or failed
      permanently, so temporary uploads never accumulate on disk.

Shall NOT:
    - Parse ECG files.
    - Detect format.
    - Validate content.

Input:
    A list of (filename, content) pairs.

Output:
    UploadSession
"""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.ecg.constants import MAX_UPLOAD_SIZE_BYTES
from app.ingestion.exceptions import DuplicateFilenameError, UploadTooLargeError


@dataclass(frozen=True)
class UploadSession:
    """A received-but-not-yet-processed upload (Implementation Spec 3.3)."""

    upload_id: str
    files: tuple[Path, ...]
    uploaded_at: datetime
    session_dir: Path


class UploadOrchestrator:
    """Receives uploaded files and creates an UploadSession without inspecting their content."""

    def __init__(self, temp_root: str | Path | None = None, max_upload_size_bytes: int = MAX_UPLOAD_SIZE_BYTES) -> None:
        self._temp_root = Path(temp_root) if temp_root is not None else Path(get_settings().ecg_upload_temp_dir)
        self._max_upload_size_bytes = max_upload_size_bytes

    def create_session(self, files: list[tuple[str, bytes]]) -> UploadSession:
        total_size = sum(len(content) for _, content in files)
        if total_size > self._max_upload_size_bytes:
            raise UploadTooLargeError(
                f"Upload size {total_size} bytes exceeds the maximum allowed size of "
                f"{self._max_upload_size_bytes} bytes."
            )

        names = [Path(filename).name for filename, _ in files]
        seen: set[str] = set()
        for name in names:
            if name in seen:
                raise DuplicateFilenameError(
                    f"Upload contains duplicate filename {name!r}; each file in a recording must be unique."
                )
            seen.add(name)

        upload_id = str(uuid.uuid4())
        session_dir = self._temp_root / upload_id
        session_dir.mkdir(parents=True, exist_ok=True)

        saved_files: list[Path] = []
        for filename, content in files:
            destination = session_dir / Path(filename).name
            destination.write_bytes(content)
            saved_files.append(destination)

        return UploadSession(
            upload_id=upload_id,
            files=tuple(saved_files),
            uploaded_at=datetime.now(timezone.utc),
            session_dir=session_dir,
        )

    def cleanup_session(self, session: UploadSession) -> None:
        """Removes the temporary upload directory for one session.

        Safe to call after either a successful or a permanently failed
        ingestion run; safe to call more than once.
        """
        shutil.rmtree(session.session_dir, ignore_errors=True)

    def get_session(self, upload_id: str) -> UploadSession:
        """Re-opens a staged upload for an asynchronous worker.

        Only a UUID-shaped direct child of the configured staging root is
        accepted, preventing a persisted or caller-supplied value from being
        used for path traversal.
        """
        try:
            normalized = str(uuid.UUID(upload_id))
        except ValueError as exc:
            raise FileNotFoundError(f"Invalid upload session {upload_id!r}") from exc
        session_dir = self._temp_root / normalized
        if not session_dir.is_dir():
            raise FileNotFoundError(f"Upload session {upload_id!r} is no longer available")
        files = tuple(sorted(path for path in session_dir.iterdir() if path.is_file()))
        if not files:
            raise FileNotFoundError(f"Upload session {upload_id!r} contains no files")
        return UploadSession(
            upload_id=normalized,
            files=files,
            uploaded_at=datetime.fromtimestamp(session_dir.stat().st_mtime, tz=timezone.utc),
            session_dir=session_dir,
        )
