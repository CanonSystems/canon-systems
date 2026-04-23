"""synthesis package."""
from synthesis.generator import VaultBundle, generate_vault
from synthesis.publisher import PublishResult, SynthesisPublisher
from synthesis.redaction import SafeEvent, project_safe, shorthash
from synthesis.sources import (
    EventSource,
    InMemoryEventSource,
    SourceError,
    StateApiEventSource,
)

__all__ = [
    "EventSource",
    "InMemoryEventSource",
    "PublishResult",
    "SafeEvent",
    "SourceError",
    "StateApiEventSource",
    "SynthesisPublisher",
    "VaultBundle",
    "generate_vault",
    "project_safe",
    "shorthash",
]
