"""Durability backup for the filesystem artifact stores, via Cloudinary.

Local disk is the fast path everywhere in both artifact stores
(``app/storage/file/filesystem.py``, ``app/reporting/storage/artifact_store.py``)
and every downstream reader (waveform loading, PDF/HTML download streaming)
keeps reading a real local path -- nothing about that changes here. This
module exists because some hosts (e.g. a Render web service with no
persistent disk attached) wipe local disk on every restart/redeploy, so a
record written by one request can be gone by the time a later request reads
it back. Cloudinary is read from only on that cache-miss path.

A record's artifact at ``(record_id, relative_path)`` maps to the Cloudinary
public_id ``{prefix}/{record_id}/{relative_path}`` deterministically -- no
separate index of what was uploaded is kept or needed; the read path
reconstructs the same public_id and asks Cloudinary for it directly.

Every resource is uploaded as ``resource_type="raw"`` (these are data files,
not images) and ``type="private"`` (signed delivery, not publicly listable --
these can be real patient ECG data). Upload/delete are best-effort: a backup
failure is logged and swallowed rather than failing the request that's
writing the primary (local) copy. Download raises on failure, since reaching
this path at all already means the local copy is gone -- a download failure
here means the data is genuinely unavailable.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.cloudinary_cloud_name and settings.cloudinary_api_key and settings.cloudinary_api_secret)


def _configure() -> None:
    settings = get_settings()
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


def upload(public_id: str, data: bytes, *, required: bool = False) -> str | None:
    """Uploads one private artifact and returns its durable public id.

    Legacy/report callers may retain best-effort behavior. Canonical ECG
    ingestion passes ``required=True`` so a missing object-store write is a
    storage failure, never a successful canonical record.
    """
    if not is_configured():
        if required:
            raise RuntimeError("Cloudinary durable storage is required but is not configured")
        return None
    try:
        _configure()
        cloudinary.uploader.upload(data, public_id=public_id, resource_type="raw", type="private", overwrite=True)
        return public_id
    except Exception:
        logger.exception("cloudinary backup upload failed for %s", public_id)
        if required:
            raise
        return None


def download(public_id: str) -> bytes:
    """Fetches one artifact's bytes. Raises if it's not configured or not found."""
    if not is_configured():
        raise FileNotFoundError(f"No local copy of {public_id!r}, and no Cloudinary backup is configured")
    _configure()
    url, _ = cloudinary.utils.cloudinary_url(public_id, resource_type="raw", type="private", sign_url=True)
    response = httpx.get(url, timeout=get_settings().artifact_download_timeout_seconds)
    response.raise_for_status()
    return response.content


def list_prefix(prefix: str) -> list[str]:
    """Lists every public_id backed up under a prefix. Returns [] if not
    configured, if nothing is backed up there, or on error -- callers treat
    an empty list the same as "nothing to restore", not as a hard failure.
    """
    if not is_configured():
        return []
    try:
        _configure()
        public_ids: list[str] = []
        next_cursor = None
        while True:
            kwargs = {"type": "private", "resource_type": "raw", "prefix": prefix, "max_results": 500}
            if next_cursor:
                kwargs["next_cursor"] = next_cursor
            result = cloudinary.api.resources(**kwargs)
            public_ids.extend(resource["public_id"] for resource in result.get("resources", []))
            next_cursor = result.get("next_cursor")
            if not next_cursor:
                break
        return public_ids
    except Exception:  # noqa: BLE001 -- listing failure degrades to "nothing found", never raises
        logger.exception("cloudinary backup listing failed for prefix %s", prefix)
        return []


def delete_prefix(prefix: str) -> None:
    """Best-effort removal of every backed-up artifact under a record/job's prefix.

    ``invalidate=True`` asks Cloudinary to purge any CDN-cached response for
    these URLs immediately rather than waiting out its TTL -- deletion at
    the origin is immediate either way, this only closes the short window
    where a signed URL fetched moments earlier could still hit a cached
    response. Never raises.
    """
    if not is_configured():
        return
    try:
        _configure()
        cloudinary.api.delete_resources_by_prefix(prefix, resource_type="raw", type="private", invalidate=True)
    except Exception:  # noqa: BLE001 -- a backup cleanup failure must not fail the caller's own cleanup
        logger.exception("cloudinary backup cleanup failed for prefix %s", prefix)
