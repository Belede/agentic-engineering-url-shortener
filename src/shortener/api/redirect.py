"""GET /{code} — resolve and redirect. FR-004, FR-005, FR-030 (CL-02)."""
import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, RedirectResponse

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


@router.get("/{code}", response_model=None)
def redirect(code: str, conn: sqlite3.Connection = Depends(get_db)) -> RedirectResponse | JSONResponse:
    link = links_repository.get_link(conn, code)

    if link is None:
        return JSONResponse(
            status_code=404,
            content={"error": "NOT_FOUND", "message": "Unknown short code"},
        )

    if _is_expired(link.expires_at):
        # Atomic: decision + analytics event in the same transaction (ADR-011).
        record_redirect_event(conn, code, outcome="expired")
        conn.commit()
        return JSONResponse(
            status_code=410,
            content={"error": "LINK_EXPIRED", "message": "Link has expired"},
        )

    # CL-02: atomic conditional UPDATE is the concurrency-safety mechanism —
    # decided before the analytics event is recorded, so a redirect is only
    # ever counted if it was actually permitted.
    outcome = links_repository.try_increment_click_count(conn, code)
    if outcome == "exhausted":
        record_redirect_event(conn, code, outcome="exhausted")
        conn.commit()
        return JSONResponse(
            status_code=410,
            content={"error": "LINK_EXHAUSTED", "message": "This link has reached its maximum number of redirects."},
        )
    if outcome == "not_found":
        return JSONResponse(
            status_code=404,
            content={"error": "NOT_FOUND", "message": "Unknown short code"},
        )

    record_redirect_event(conn, code, outcome="resolved")
    conn.commit()
    return RedirectResponse(url=link.target_url, status_code=302)
