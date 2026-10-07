"""Immutable representation of parsed documents.

The Generation Context is required to stay immutable throughout pipeline
execution (Sprint 2.10). Parsed JSON documents -- ECG metadata, manifests,
preprocessing reports, and later Signal Processing payloads -- are nested
structures, so freezing only the object that holds them would leave their
contents editable by any stage that receives them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any


def freeze_document(value: Any) -> Any:
    """Recursively converts a parsed document into read-only structures.

    Mappings become ``MappingProxyType``, sequences become tuples, and scalars
    are returned unchanged. Strings and bytes are treated as scalars.
    """
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze_document(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(freeze_document(item) for item in value)
    return value
