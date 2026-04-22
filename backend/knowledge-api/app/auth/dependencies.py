"""Auth dependencies for API handlers."""

from __future__ import annotations

from fastapi import Header

from app.auth.models import ActorContext


def get_actor_context(
    x_actor_id: str | None = Header(default=None),
    x_actor_groups: str | None = Header(default=None),
    x_company_id: str | None = Header(default=None),
) -> ActorContext:
    group_ids = [part.strip() for part in (x_actor_groups or "").split(",") if part.strip()]
    company_id = x_company_id.strip() if x_company_id and x_company_id.strip() else None
    return ActorContext(actor_id=x_actor_id or "usr_system", group_ids=group_ids, company_id=company_id)


def get_company_scope_id(
    x_company_id: str | None = Header(default=None),
) -> str | None:
    if x_company_id is None:
        return None
    stripped = x_company_id.strip()
    return stripped or None
