"""T034: metrics registry, MTTR calculation with a known-expected-value case.
FR-026, NFR-005, ADR-008, plan.md §6 MTTR formula.

MTTR = Total recovery duration across recovered events / Number of recovered events.
Unrecovered failures are excluded from the denominator and reported separately.
"""
from pathlib import Path

import pytest

from orchestration.engine import create_run, transition
from orchestration.telemetry.metrics import compute_metrics, compute_mttr
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "metrics.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


def test_mttr_excludes_unrecovered_failures_from_denominator(conn):
    """Known-expected-value case: two recovered failures (10s and 20s
    recovery) and one unrecovered -> MTTR = (10+20)/2 = 15s, unrecovered
    count = 1, recovered count = 2."""
    run_a = create_run(conn, requirement_input="a", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_a, to_state="QUALITY_CHECK", actor="system", reason="x")
    transition(conn, run_a, to_state="DECOMPOSE", actor="system", reason="x")
    transition(conn, run_a, to_state="DESIGN", actor="system", reason="x")
    transition(conn, run_a, to_state="ARCH_APPROVAL", actor="system", reason="x")
    transition(conn, run_a, to_state="SAFE_STOP", actor="human", reason="rejected")
    conn.execute(
        "UPDATE state_transitions SET occurred_at='2026-01-01T00:00:00.000000Z' "
        "WHERE run_id=? AND to_state='SAFE_STOP'", (run_a,),
    )
    conn.execute(
        "INSERT INTO audit_events (run_id, actor_type, action, affected_artifact, result, reason, occurred_at) "
        "VALUES (?, 'human', 'resume', ?, 'success', 'fixed', '2026-01-01T00:00:10.000000Z')",
        (run_a, f"workflow_runs:{run_a}"),
    )

    run_b = create_run(conn, requirement_input="b", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_b, to_state="QUALITY_CHECK", actor="system", reason="x")
    transition(conn, run_b, to_state="DECOMPOSE", actor="system", reason="x")
    transition(conn, run_b, to_state="DESIGN", actor="system", reason="x")
    transition(conn, run_b, to_state="ARCH_APPROVAL", actor="system", reason="x")
    transition(conn, run_b, to_state="SAFE_STOP", actor="human", reason="rejected")
    conn.execute(
        "UPDATE state_transitions SET occurred_at='2026-01-01T00:00:00.000000Z' "
        "WHERE run_id=? AND to_state='SAFE_STOP'", (run_b,),
    )
    conn.execute(
        "INSERT INTO audit_events (run_id, actor_type, action, affected_artifact, result, reason, occurred_at) "
        "VALUES (?, 'human', 'resume', ?, 'success', 'fixed', '2026-01-01T00:00:20.000000Z')",
        (run_b, f"workflow_runs:{run_b}"),
    )

    run_c = create_run(conn, requirement_input="c", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_c, to_state="QUALITY_CHECK", actor="system", reason="x")
    transition(conn, run_c, to_state="DECOMPOSE", actor="system", reason="x")
    transition(conn, run_c, to_state="DESIGN", actor="system", reason="x")
    transition(conn, run_c, to_state="ARCH_APPROVAL", actor="system", reason="x")
    transition(conn, run_c, to_state="SAFE_STOP", actor="human", reason="rejected")
    # run_c never resumes — unrecovered.
    conn.commit()

    result = compute_mttr(conn)

    assert result.recovered_count == 2
    assert result.unrecovered_count == 1
    assert result.mttr_seconds == pytest.approx(15.0)
    assert result.total_recovery_duration_seconds == pytest.approx(30.0)


def test_compute_metrics_includes_success_rate_and_counts(conn):
    run_done = create_run(conn, requirement_input="a", scenario_type="greenfield", policy_pack_version="1.0.0")
    conn.execute("UPDATE workflow_runs SET current_state='DONE', terminal_status='DONE' WHERE run_id=?", (run_done,))
    run_stopped = create_run(conn, requirement_input="b", scenario_type="greenfield", policy_pack_version="1.0.0")
    conn.execute("UPDATE workflow_runs SET current_state='SAFE_STOP' WHERE run_id=?", (run_stopped,))
    conn.commit()

    metrics = compute_metrics(conn)
    assert metrics["success_rate"] == pytest.approx(0.5)
    assert "mttr_seconds" in metrics
    assert "unrecovered_failure_count" in metrics
    assert metrics["demonstration_data"] is True
