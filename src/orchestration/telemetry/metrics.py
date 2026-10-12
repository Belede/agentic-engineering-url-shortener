"""Reliability metrics derived from the persisted event stream (audit_events,
state_transitions, workflow_runs) — never from hand-maintained counters that
could drift from reality (ADR-008). FR-026, NFR-005.

MTTR = Total recovery duration across recovered events / Number of recovered events.
Unrecovered failures are excluded from the MTTR denominator and reported
separately (plan.md §6; constitution Principle IX: demonstration measurements
must be clearly distinguished from production measurements — see
`demonstration_data` in compute_metrics()).
"""
import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MTTRResult:
    recovered_count: int
    unrecovered_count: int
    total_recovery_duration_seconds: float
    mttr_seconds: float | None  # None when recovered_count == 0 — never divide by zero


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)  # Python 3.11+ parses the "Z" suffix natively


def compute_mttr(conn: sqlite3.Connection) -> MTTRResult:
    failures = conn.execute(
        "SELECT run_id, occurred_at FROM state_transitions WHERE to_state = 'SAFE_STOP' ORDER BY occurred_at"
    ).fetchall()

    recovered_durations: list[float] = []
    unrecovered_count = 0

    for failure in failures:
        run_id, detected_at = failure["run_id"], failure["occurred_at"]
        resume = conn.execute(
            "SELECT occurred_at FROM audit_events "
            "WHERE run_id = ? AND action = 'resume' AND occurred_at > ? "
            "ORDER BY occurred_at LIMIT 1",
            (run_id, detected_at),
        ).fetchone()
        if resume is None:
            unrecovered_count += 1
            continue
        duration = (_parse_ts(resume["occurred_at"]) - _parse_ts(detected_at)).total_seconds()
        recovered_durations.append(duration)

    total = sum(recovered_durations)
    mttr = (total / len(recovered_durations)) if recovered_durations else None

    return MTTRResult(
        recovered_count=len(recovered_durations),
        unrecovered_count=unrecovered_count,
        total_recovery_duration_seconds=total,
        mttr_seconds=mttr,
    )


def compute_metrics(conn: sqlite3.Connection) -> dict:
    total_terminal = conn.execute(
        "SELECT COUNT(*) FROM workflow_runs WHERE current_state IN ('DONE', 'SAFE_STOP')"
    ).fetchone()[0]
    done = conn.execute(
        "SELECT COUNT(*) FROM workflow_runs WHERE current_state = 'DONE'"
    ).fetchone()[0]
    success_rate = (done / total_terminal) if total_terminal else None

    retry_count = conn.execute(
        "SELECT COUNT(*) FROM audit_events WHERE action = 'retry'"
    ).fetchone()[0]
    rollback_count = conn.execute(
        "SELECT COUNT(*) FROM audit_events WHERE action = 'rollback'"
    ).fetchone()[0]
    compensation_count = conn.execute(
        "SELECT COUNT(*) FROM audit_events WHERE action = 'compensation'"
    ).fetchone()[0]

    mttr = compute_mttr(conn)

    return {
        "success_rate": success_rate,
        "retry_count": retry_count,
        "rollback_count": rollback_count,
        "compensation_count": compensation_count,
        "mttr_seconds": mttr.mttr_seconds,
        "recovered_failure_count": mttr.recovered_count,
        "unrecovered_failure_count": mttr.unrecovered_count,
        "total_recovery_duration_seconds": mttr.total_recovery_duration_seconds,
        # Explicit per constitution Principle IX: these numbers come from
        # whatever runs exist in this database (typically the required
        # scenario + fault-injection demonstration runs), never from
        # production traffic — never present as a production SLA.
        "demonstration_data": True,
    }
