"""Upload Status Store (Upload Layer).

Purpose:
    Persist upload processing status so that GET /uploads/{upload_id}
    (Implementation Spec 17.11) reflects the correct state even after an
    application restart. An in-memory dict does not survive a process
    restart, which would make every in-flight or completed upload
    unreachable the moment the service restarts -- unacceptable for a
    production deployment.

    Phase 1 uses a lightweight JSON-file-per-upload store under a
    dedicated directory. This keeps the Upload Layer free of a database
    dependency while still surviving restarts; a future phase may swap in
    a database-backed implementation without changing the Service layer,
    since callers only depend on the `get`/`set` contract below
    (Repository Pattern).

Shall NOT:
    - Parse ECG files.
    - Store ECGRecord data -- only the upload lifecycle (state, the
      resulting record_id once known, and a failure detail message).

Input:
    UploadStatus (upload_id, state, record_id, detail)

Output:
    UploadStatus | None
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.config import get_settings


@dataclass(frozen=True)
class UploadStatus:
    """The persisted lifecycle state of one upload."""

    upload_id: str
    state: str
    record_id: str | None = None
    detail: str | None = None


class UploadStatusStore:
    """Persists per-upload processing status as one JSON file per upload_id."""

    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(root) if root is not None else Path(get_settings().ecg_upload_status_dir)

    def _path(self, upload_id: str) -> Path:
        return self._root / f"{upload_id}.json"

    def set(self, status: UploadStatus) -> None:
        path = self._path(status.upload_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(status)), encoding="utf-8")

    def get(self, upload_id: str) -> UploadStatus | None:
        path = self._path(upload_id)
        if not path.exists():
            return None
        return UploadStatus(**json.loads(path.read_text(encoding="utf-8")))
