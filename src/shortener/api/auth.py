"""API-key auth dependency. CL-06: attribution/rate-limit scoping only, not
a production authentication system — documented limitation (ADR-011)."""
import sqlite3

from fastapi import Depends, Header, HTTPException

from shortener.api.deps import get_db
from shortener.persistence import api_keys_repository


def require_api_key(
    x_api_key: str | None = Header(default=None),
    conn: sqlite3.Connection = Depends(get_db),
) -> str:
    if not x_api_key or not api_keys_repository.key_exists(conn, x_api_key):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")
    return x_api_key
