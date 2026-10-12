"""Orchestration engine loop: create/transition workflow runs, persisting
state and audit evidence as it goes. ADR-004 (persistence), ADR-008 (audit),
FR-011 (persisted state), FR-025 (audit evidence)."""
import sqlite3
import uuid

from orchestration.graph import is_valid_transition


class InvalidTransitionError(RuntimeError):
    """Raised when a requested transition is not declared in the graph, or
    is declared for a different actor (e.g. a 'system' actor attempting to
    leave a human-gate node) — see graph.py TRANSITIONS and ADR-005."""


def create_run(
    conn: sqlite3.Connection,
    requirement_input: str,
    scenario_type: str,
    policy_pack_version: str,
) -> str:
    run_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO workflow_runs (run_id, requirement_input, scenario_type, "
        "current_state, policy_pack_version) VALUES (?, ?, ?, 'INGEST', ?)",
        (run_id, requirement_input, scenario_type, policy_pack_version),
    )
    _record_transition(conn, run_id, from_state=None, to_state="INGEST", actor="system",
                        reason="run created")
    conn.commit()
    return run_id


def get_run(conn: sqlite3.Connection, run_id: str) -> dict:
    row = conn.execute(
        "SELECT run_id, requirement_input, scenario_type, current_state, "
        "policy_pack_version, terminal_status, created_at, updated_at "
        "FROM workflow_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"No such run: {run_id}")
    return dict(row)


def transition(
    conn: sqlite3.Connection,
    run_id: str,
    to_state: str,
    actor: str,
    reason: str,
) -> None:
    run = get_run(conn, run_id)
    from_state = run["current_state"]

    if not is_valid_transition(from_state, to_state, actor):
        raise InvalidTransitionError(
            f"{from_state!r} -> {to_state!r} not permitted for actor={actor!r}"
        )

    conn.execute(
        "UPDATE workflow_runs SET current_state = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') "
        "WHERE run_id = ?",
        (to_state, run_id),
    )
    _record_transition(conn, run_id, from_state=from_state, to_state=to_state, actor=actor, reason=reason)
    conn.commit()


def _record_transition(
    conn: sqlite3.Connection,
    run_id: str,
    from_state: str | None,
    to_state: str,
    actor: str,
    reason: str,
) -> None:
    conn.execute(
        "INSERT INTO state_transitions (run_id, from_state, to_state, actor, reason) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_id, from_state, to_state, actor, reason),
    )
    conn.execute(
        "INSERT INTO audit_events (run_id, actor_type, action, affected_artifact, result, reason) "
        "VALUES (?, ?, 'state_transition', ?, 'success', ?)",
        (run_id, actor, f"workflow_runs:{run_id}", reason),
    )
