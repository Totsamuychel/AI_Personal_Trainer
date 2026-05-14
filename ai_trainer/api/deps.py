"""Shared FastAPI dependencies."""
import os
import secrets
from typing import Optional

from fastapi import Header, HTTPException, status


def _keys_match(provided: str, expected: str) -> bool:
    try:
        return secrets.compare_digest(provided, expected)
    except (TypeError, ValueError):
        return False


async def verify_admin_api_key(
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    authorization: Optional[str] = Header(None),
) -> None:
    """When ADMIN_API_KEY is set, require X-Admin-API-Key or Authorization: Bearer <key>."""
    expected = (os.getenv("ADMIN_API_KEY") or "").strip()
    if not expected:
        return

    provided = (x_admin_api_key or "").strip()
    if not provided and authorization:
        auth = authorization.strip()
        if auth.lower().startswith("bearer "):
            provided = auth[7:].strip()

    if not provided or not _keys_match(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key",
        )
