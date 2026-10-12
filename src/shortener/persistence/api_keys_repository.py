"""api_keys repository. CL-06."""
import sqlite3


def create_key(conn: sqlite3.Connection, key_id: str, label: str) -> None:
    conn.execute(
        "INSERT INTO api_keys (key_id, label) VALUES (?, ?)", (key_id, label)
    )
    conn.commit()


def key_exists(conn: sqlite3.Connection, key_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM api_keys WHERE key_id = ?", (key_id,)
    ).fetchone()
    return row is not None
