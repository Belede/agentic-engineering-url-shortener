"""DECOMPOSE node: record task decomposition, transition to DESIGN. FR-011."""
import sqlite3

from orchestration.engine import transition


def run_decompose(conn: sqlite3.Connection, run_id: str, summary: str) -> None:
    conn.execute(
        "INSERT INTO decisions (run_id, decision_type, content) VALUES (?, 'decomposition', ?)",
        (run_id, summary),
    )
    conn.commit()
    transition(conn, run_id, to_state="DESIGN", actor="system", reason="decomposition complete")
