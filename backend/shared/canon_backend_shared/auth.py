"""Authentication helpers for backend services (stub until E2-T2 / E1-T2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(slots=True)
class AuthContext:
    """Empty placeholder; real fields arrive with caller identity work."""


def verify_caller(headers: Mapping[str, str]) -> AuthContext:
    """
    Verify the caller from HTTP headers and return an AuthContext.

    Real authentication and authorization land in E2-T2 and E1-T2; this stub
    intentionally fails so tests do not accidentally treat unauthenticated
    traffic as trusted.
    """
    raise NotImplementedError("real auth lands in E2-T2 / E1-T2")
