"""Client exceptions."""

from __future__ import annotations


class KnowledgeClientError(RuntimeError):
    """Base error raised by the Canon Systems v2 client."""


class KnowledgeClientResponseError(KnowledgeClientError):
    """Raised when an upstream service returns a non-success response."""

    def __init__(self, *, service: str, method: str, url: str, status_code: int, body: str) -> None:
        message = f"{service} request failed: {method} {url} -> {status_code}"
        if body:
            message = f"{message}: {body}"
        super().__init__(message)
        self.service = service
        self.method = method
        self.url = url
        self.status_code = status_code
        self.body = body
