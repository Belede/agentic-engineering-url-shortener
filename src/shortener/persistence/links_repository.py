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
) -> ShortLink:
    conn.execute(
        "INSERT INTO short_links (code, target_url, created_by, expires_at) "
        "VALUES (?, ?, ?, ?)",
        (code, target_url, created_by, expires_at),
    )
    conn.commit()
    return get_link(conn, code)


def get_link(conn: sqlite3.Connection, code: str) -> ShortLink | None:
    row = conn.execute(
        "SELECT code, target_url, created_by, created_at, expires_at, "
        "click_count, status FROM short_links WHERE code = ?",
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
    )
