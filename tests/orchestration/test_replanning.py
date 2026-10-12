"""T032: RENORMALIZE — dynamic replanning with a real before/after task diff,
scoped to affected tasks only. FR-018, ADR-007."""
from pathlib import Path

import pytest

from orchestration.engine import create_run, get_run, transition
from orchestration.nodes.renormalize import run_renormalize
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def run_at_renormalize(tmp_path):
    conn = get_connection(str(tmp_path / "replan.db"))
    MigrationRunner(conn, MIGRATIONS_DIR).apply_all()
    run_id = create_run(conn, requirement_input="ambiguous text", scenario_type="ambiguous", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="x")
    transition(conn, run_id, to_state="CLARIFY", actor="system", reason="ambiguity detected")
    transition(conn, run_id, to_state="RENORMALIZE", actor="human", reason="human answered")
    yield conn, run_id
    conn.close()


def test_renormalize_transitions_to_decompose(run_at_renormalize):
    conn, run_id = run_at_renormalize
    run_renormalize(
        conn, run_id,
        new_requirement_text="New links only get a 90-day default expiry; existing links never change.",
        prior_tasks=["task: implement expiry"],
        new_tasks=["task: add SHORTENER_DEFAULT_TTL_DAYS config", "task: apply default only to new links"],
    )
    assert get_run(conn, run_id)["current_state"] == "DECOMPOSE"


def test_renormalize_computes_a_real_diff_not_a_full_discard(run_at_renormalize):
    """ADR-007: scoped regeneration, not a full restart that destroys lineage."""
    conn, run_id = run_at_renormalize
    diff = run_renormalize(
        conn, run_id,
        new_requirement_text="New links only get a 90-day default expiry; existing links never change.",
        prior_tasks=["task: implement expiry", "task: shared baseline validation"],
        new_tasks=["task: add SHORTENER_DEFAULT_TTL_DAYS config", "task: shared baseline validation"],
    )
    assert diff["added"] == ["task: add SHORTENER_DEFAULT_TTL_DAYS config"]
    assert diff["removed"] == ["task: implement expiry"]
    assert diff["unchanged"] == ["task: shared baseline validation"]


def test_renormalize_records_a_replan_decision_with_the_diff(run_at_renormalize):
    conn, run_id = run_at_renormalize
    run_renormalize(
        conn, run_id,
        new_requirement_text="x",
        prior_tasks=["a"],
        new_tasks=["b"],
    )
    row = conn.execute(
        "SELECT decision_type, content FROM decisions WHERE run_id = ? AND decision_type = 'replan'",
        (run_id,),
    ).fetchone()
    assert row is not None
    assert "added" in row["content"] and "removed" in row["content"]


def test_renormalize_records_a_replanning_audit_event(run_at_renormalize):
    conn, run_id = run_at_renormalize
    run_renormalize(conn, run_id, new_requirement_text="x", prior_tasks=["a"], new_tasks=["b"])
    row = conn.execute(
        "SELECT action FROM audit_events WHERE run_id = ? AND action = 'replanning'",
        (run_id,),
    ).fetchone()
    assert row is not None
