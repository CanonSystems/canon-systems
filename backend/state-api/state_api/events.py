"""Canonical event emission (historical plane)."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import asdict
from canon_backend_shared.events import CanonicalEvent

EventEmitter = Callable[[CanonicalEvent], None]

_logger = logging.getLogger("state_api.events")


def _default_emitter(event: CanonicalEvent) -> None:
    line = json.dumps(asdict(event), default=str)
    _logger.info("%s", line)


def get_event_emitter() -> EventEmitter:
    """FastAPI dependency: default sink logs one JSON line per event."""
    return _default_emitter
