"""Rollback: used for changes that have NOT yet been applied externally
(still reversible by simply discarding them). ADR-006, FR-023.

is_rollback_feasible is an explicit, testable predicate — not an implicit
judgment call buried in a conditional (independent-review condition #2).
"""
import sqlite3
from dataclasses import dataclass


@dataclass
class Change:
    description: str
    applied_externally: bool  # has this left the sandbox / been applied anywhere rollback can't cleanly reach?


class RollbackInfeasibleError(RuntimeError):
    """Raised when rollback is attempted on a change that has already been
    applied externally — the caller must route to compensation instead."""


def is_rollback_feasible(change: Change) -> bool:
    return not change.applied_externally


def rollback(conn: sqlite3.Connection, run_id: str, change: Change) -> None:
    if not is_rollback_feasible(change):
        raise RollbackInfeasibleError(
            f"Cannot roll back '{change.description}' — already applied externally; use compensation"
        )
    conn.execute(
        "INSERT INTO audit_events (run_id, actor_type, action, affected_artifact, result, reason) "
        "VALUES (?, 'system', 'rollback', ?, 'success', ?)",
        (run_id, change.description, f"rolled back: {change.description}"),
    )
    conn.commit()
