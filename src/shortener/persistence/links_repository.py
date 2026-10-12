"""short_links repository. FR-001 through FR-010, CL-07."""
import sqlite3
from dataclasses import dataclass


@dataclass
class ShortLink:
    code: str
    target_url: str
    created_by: str
    created_at: str
    expires_at: str | None
    click_count: int
    status: str
    max_clicks: int | None = None


def code_exists(conn: sqlite3.Connection, code: str) -> bool:
    row = conn.execute("SELECT 1 FROM short_links WHERE code = ?", (code,)).fetchone()
    return row is not None


def create_link(
    conn: sqlite3.Connection,
    code: str,
    target_url: str,
    created_by: str,
    expires_at: str | None,
    max_clicks: int | None = None,
) -> ShortLink:
    conn.execute(
        "INSERT INTO short_links (code, target_url, created_by, expires_at, max_clicks) "
        "VALUES (?, ?, ?, ?, ?)",
        (code, target_url, created_by, expires_at, max_clicks),
    )
    conn.commit()
    return get_link(conn, code)


def get_link(conn: sqlite3.Connection, code: str) -> ShortLink | None:
    row = conn.execute(
        "SELECT code, target_url, created_by, created_at, expires_at, "
        "click_count, status, max_clicks FROM short_links WHERE code = ?",
        (code,),
    ).fetchone()
    if row is None:
        return None
    return ShortLink(
        code=row["code"],
        target_url=row["target_url"],
        created_by=row["created_by"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        click_count=row["click_count"],
        status=row["status"],
        max_clicks=row["max_clicks"],
    )


def try_increment_click_count(conn: sqlite3.Connection, code: str) -> str:
    """Atomic, concurrency-safe click-count increment (CL-02, brownfield).

    A single UPDATE ... WHERE clause is the concurrency-safety mechanism —
    not an application-level lock (ADR-003 precedent). Returns:
      "resolved"   — incremented successfully, redirect may proceed
      "exhausted"  — max_clicks reached, no row updated
      "not_found"  — no such code
    """
    cursor = conn.execute(
        "UPDATE short_links SET click_count = click_count + 1 "
        "WHERE code = ? AND (max_clicks IS NULL OR click_count < max_clicks)",
        (code,),
    )
    conn.commit()
    if cursor.rowcount == 1:
        return "resolved"

    # No row updated — either the link doesn't exist, or it's exhausted.
    exists = conn.execute("SELECT 1 FROM short_links WHERE code = ?", (code,)).fetchone()
    return "exhausted" if exists else "not_found"
