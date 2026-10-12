"""Compensation: used once a change has propagated beyond clean rollback
reach (irreversible). Always human-approved — never automatic. ADR-006, FR-023."""
import sqlite3
from dataclasses import dataclass


@dataclass
class CompensatingAction:
    change_description: str
    compensating_control: str
    approved_by: str  # must be a non-empty human identity — compensation is never automatic


class CompensationNotApprovedError(RuntimeError):
    """Raised when no human approver identity is present."""


def compensate(conn: sqlite3.Connection, run_id: str, action: CompensatingAction) -> None:
    if not action.approved_by:
        raise CompensationNotApprovedError(
            "Compensation requires an explicit human approver (ADR-006: never automatic)"
        )
    conn.execute(
        "INSERT INTO audit_events (run_id, actor_type, action, affected_artifact, result, reason) "
        "VALUES (?, 'human', 'compensation', ?, 'success', ?)",
        (
            run_id,
            action.change_description,
            f"compensated by {action.approved_by}: {action.compensating_control}",
        ),
    )
    conn.commit()
