"""Policy-exception workflow: explicit human approval, rationale, scope,
compensating control, and expiry — constitution Principle VI. An exception
is never inferred or self-approved; apply_exception() structurally requires
a non-empty approving_authority."""
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class PolicyException:
    policy_id: str
    reason: str
    scope: str
    approving_authority: str
    compensating_control: str
    expires_at: str  # ISO8601


class ExceptionNotApprovedError(RuntimeError):
    """Raised when no human approving authority is present."""


def apply_exception(conn: sqlite3.Connection, exc: PolicyException) -> int:
    if not exc.approving_authority:
        raise ExceptionNotApprovedError(
            "Policy exception requires an explicit human approving authority"
        )
    cursor = conn.execute(
        "INSERT INTO policy_exceptions "
        "(policy_id, reason, scope, approving_authority, compensating_control, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (exc.policy_id, exc.reason, exc.scope, exc.approving_authority,
         exc.compensating_control, exc.expires_at),
    )
    conn.commit()
    return cursor.lastrowid


def is_exception_valid(conn: sqlite3.Connection, exception_id: int) -> bool:
    row = conn.execute(
        "SELECT expires_at FROM policy_exceptions WHERE id = ?", (exception_id,)
    ).fetchone()
    if row is None:
        return False
    expires_at = datetime.fromisoformat(row["expires_at"])
    return datetime.now(UTC) < expires_at
