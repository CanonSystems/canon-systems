"""Authenticated actor context."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ActorContext(BaseModel):
    actor_id: str = Field(default="usr_system")
    group_ids: list[str] = Field(default_factory=list)
    company_id: str | None = None
