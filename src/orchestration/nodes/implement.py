"""IMPLEMENT node: records human-supervised implementation evidence,
transitions to TEST. constitution Principle IV/VII."""
import sqlite3

from orchestration.engine import transition


def run_implement(conn: sqlite3.Connection, run_id: str, summary: str) -> None:
    conn.execute(
        "INSERT INTO audit_events (run_id, actor_type, action, affected_artifact, result, reason) "
        "VALUES (?, 'human', 'implementation_recorded', ?, 'success', ?)",
        (run_id, f"workflow_runs:{run_id}", summary),
    )
    conn.commit()
    transition(conn, run_id, to_state="TEST", actor="system", reason="implementation complete")
