from __future__ import annotations
from fastapi import Depends, Header, HTTPException
from .config import Settings, get_settings


def bearer_auth(
    authorization: str | None = Header(default=None), settings: Settings = Depends(get_settings)
) -> None:
    if not authorization:
        raise HTTPException(status_code=401, detail="missing_authorization")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid_authorization_scheme")
    token = authorization[len("Bearer ") :].strip()
    if token != settings.service_token:
        raise HTTPException(status_code=403, detail="invalid_token")
