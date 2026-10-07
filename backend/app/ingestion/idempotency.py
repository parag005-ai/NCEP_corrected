"""Deterministic identities for asynchronous ECG ingestion requests."""

from __future__ import annotations

import hashlib


def request_fingerprint(patient_id: str, files: list[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    digest.update(patient_id.encode("utf-8"))
    for name, content in sorted(files, key=lambda item: item[0].lower()):
        digest.update(b"\0")
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()


def effective_idempotency_key(
    *, organisation_id: str, requested_by_user_id: str, fingerprint: str, supplied_key: str | None
) -> str:
    scope = f"{organisation_id}:{requested_by_user_id}:{supplied_key or fingerprint}"
    return hashlib.sha256(scope.encode("utf-8")).hexdigest()
