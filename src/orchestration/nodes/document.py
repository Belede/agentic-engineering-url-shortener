"""DOCUMENT node: generate docs, falling back to a labeled stub on failure
rather than blocking the run. ADR-006 fallback behavior."""
import sqlite3
from collections.abc import Callable

from orchestration.engine import transition

FALLBACK_LABEL = "[fallback: doc-generator unavailable]"


def run_document(conn: sqlite3.Connection, run_id: str, generate_docs: Callable[[], str]) -> None:
    try:
        content = generate_docs()
    except Exception as exc:  # noqa: BLE001 — any doc-generator failure triggers the fallback
        content = f"{FALLBACK_LABEL} {exc}"

    conn.execute(
        "INSERT INTO decisions (run_id, decision_type, content) VALUES (?, 'documentation', ?)",
        (run_id, content),
    )
    conn.commit()
    transition(conn, run_id, to_state="RELEASE_APPROVAL", actor="system", reason="documentation stage complete")
