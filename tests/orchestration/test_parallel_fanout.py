"""T024: TEST node — genuine parallel fan-out/fan-in across unit/contract/security
groups, synchronized before DOCUMENT. This is the orchestration's concrete
parallelism evidence (Independent Reviewer Gate review question #2/#3)."""
from pathlib import Path

import pytest

from orchestration.engine import create_run, get_run, transition
from orchestration.nodes.test_node import run_test_node
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def run_at_test(tmp_path):
    conn = get_connection(str(tmp_path / "test_node.db"))
    MigrationRunner(conn, MIGRATIONS_DIR).apply_all()
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    for to_state, actor in [
        ("QUALITY_CHECK", "system"), ("DECOMPOSE", "system"), ("DESIGN", "system"),
        ("ARCH_APPROVAL", "system"), ("IMPLEMENT", "human"), ("TEST", "system"),
    ]:
        transition(conn, run_id, to_state=to_state, actor=actor, reason="x")
    yield conn, run_id
    conn.close()


def test_all_groups_passing_transitions_to_document(run_at_test):
    conn, run_id = run_at_test
    run_test_node(conn, run_id, groups={"unit": True, "contract": True, "security": True})
    assert get_run(conn, run_id)["current_state"] == "DOCUMENT"


def test_any_group_failing_transitions_to_safe_stop(run_at_test):
    conn, run_id = run_at_test
    run_test_node(conn, run_id, groups={"unit": True, "contract": False, "security": True})
    assert get_run(conn, run_id)["current_state"] == "SAFE_STOP"


def test_each_group_produces_its_own_audit_event(run_at_test):
    conn, run_id = run_at_test
    run_test_node(conn, run_id, groups={"unit": True, "contract": True, "security": True})
    rows = conn.execute(
        "SELECT affected_artifact, result FROM audit_events "
        "WHERE run_id = ? AND action = 'test_group_executed' ORDER BY affected_artifact",
        (run_id,),
    ).fetchall()
    assert [r["affected_artifact"] for r in rows] == ["contract", "security", "unit"]
    assert all(r["result"] == "pass" for r in rows)


def test_groups_actually_execute_concurrently_not_sequentially(run_at_test):
    """Genuine parallelism evidence: overlapping wall-clock windows, not
    just three function calls in a row."""
    conn, run_id = run_at_test
    timings = run_test_node(
        conn, run_id, groups={"unit": True, "contract": True, "security": True},
        simulated_duration_seconds=0.08,
    )
    starts = [t["started_at"] for t in timings.values()]
    ends = [t["ended_at"] for t in timings.values()]
    # If truly sequential, the total span would be >= 3 * duration.
    # If parallel, the span is close to one duration.
    total_span = max(ends) - min(starts)
    assert total_span < 0.08 * 2.5  # generous margin, still proves overlap
