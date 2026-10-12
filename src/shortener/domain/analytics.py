"""Analytics: atomic RedirectEvent write in the same transaction as the
redirect decision. FR-006, FR-008, NFR-003, ADR-011."""
import sqlite3


def record_redirect_event(conn: sqlite3.Connection, code: str, outcome: str) -> None:
    conn.execute(
        "INSERT INTO redirect_events (code, outcome) VALUES (?, ?)", (code, outcome)
    )
