"""DESIGN node: record design proposal + security-sensitivity flag, transition
to ARCH_APPROVAL. FR-014, FR-015 (brownfield impact), ADR-005 conditional branch."""
import sqlite3

from orchestration.engine import transition


def run_design(
    conn: sqlite3.Connection,
    run_id: str,
    summary: str,
    security_sensitive: bool = False,
) -> None:
    conn.execute(
        "INSERT INTO decisions (run_id, decision_type, content) VALUES (?, 'design', ?)",
        (run_id, summary),
    )
    conn.execute(
        "UPDATE workflow_runs SET security_sensitive = ? WHERE run_id = ?",
        (1 if security_sensitive else 0, run_id),
    )
    conn.commit()
    transition(conn, run_id, to_state="ARCH_APPROVAL", actor="system", reason="design proposal ready")
