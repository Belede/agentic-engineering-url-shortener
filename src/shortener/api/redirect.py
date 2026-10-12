"""GET /{code} — resolve and redirect. FR-004, FR-005."""
import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from shortener.api.deps import get_db
from shortener.domain.analytics import record_redirect_event
from shortener.persistence import links_repository

router = APIRouter()


def _is_expired(expires_at: str | None) -> bool:
    if expires_at is None:
        return False
    expiry = datetime.fromisoformat(expires_at)
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    return datetime.now(UTC) >= expiry


@router.get("/{code}")
def redirect(code: str, conn: sqlite3.Connection = Depends(get_db)) -> RedirectResponse:
    link = links_repository.get_link(conn, code)

    if link is None:
        raise HTTPException(status_code=404, detail="Unknown short code")

    if _is_expired(link.expires_at):
        # Atomic: decision + analytics event in the same transaction (ADR-011).
        record_redirect_event(conn, code, outcome="expired")
        conn.commit()
        raise HTTPException(status_code=410, detail="Link has expired")

    record_redirect_event(conn, code, outcome="resolved")
    conn.commit()
    return RedirectResponse(url=link.target_url, status_code=302)
