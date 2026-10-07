from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorageInterface(ABC):
    """Contract for storage adapters used by ingestion and reporting."""

    @abstractmethod
    def store(self, payload: Any) -> Any:
        """Persist a payload through the configured storage backend."""
