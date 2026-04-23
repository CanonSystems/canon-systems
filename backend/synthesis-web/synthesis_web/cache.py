"""Per-key LRU cache keyed on (relative_path, content_hash)."""
from __future__ import annotations

from collections import OrderedDict
from typing import Any


class ContentHashCache:
    def __init__(self, max_size: int = 512) -> None:
        self._max = max_size
        self._data: OrderedDict[tuple[str, str], Any] = OrderedDict()

    def get(self, rel: str, content_hash: str) -> Any | None:
        key = (rel, content_hash)
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def set(self, rel: str, content_hash: str, value: Any) -> None:
        key = (rel, content_hash)
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self._max:
            self._data.popitem(last=False)
