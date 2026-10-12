"""idempotency_keys repository. FR-007, CL-04."""
import sqlite3


def find_existing_result(conn: sqlite3.Connection, key: str, caller_id: str) -> str | None:
    row = conn.execute(
        "SELECT result_code FROM idempotency_keys WHERE key = ? AND caller_id = ?",
        (key, caller_id),
    ).fetchone()
    return row["result_code"] if row else None


def record_result(conn: sqlite3.Connection, key: str, caller_id: str, result_code: str) -> None:
    conn.execute(
        "INSERT INTO idempotency_keys (key, caller_id, result_code) VALUES (?, ?, ?)",
        (key, caller_id, result_code),
    )
    conn.commit()
