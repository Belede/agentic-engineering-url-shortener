"""T033: audit-event completeness — one row per state transition. FR-025, NFR-006, ADR-008."""
from pathlib import Path

import pytest

from orchestration.engine import create_run, transition
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "audit.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


def test_every_state_transition_has_exactly_one_matching_audit_event(conn):
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    for to_state, actor in [
        ("QUALITY_CHECK", "system"), ("DECOMPOSE", "system"), ("DESIGN", "system"),
        ("ARCH_APPROVAL", "system"),
    ]:
        transition(conn, run_id, to_state=to_state, actor=actor, reason="x")

    transition_count = conn.execute(
        "SELECT COUNT(*) FROM state_transitions WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    audit_count = conn.execute(
        "SELECT COUNT(*) FROM audit_events WHERE run_id = ? AND action = 'state_transition'",
        (run_id,),
    ).fetchone()[0]
    assert transition_count == audit_count == 5  # INGEST + 4 transitions


def test_every_audit_event_has_required_fields_populated(conn):
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    rows = conn.execute(
        "SELECT actor_type, action, occurred_at, affected_artifact, result, reason "
        "FROM audit_events WHERE run_id = ?",
        (run_id,),
    ).fetchall()
    assert len(rows) >= 1
    for row in rows:
        assert row["actor_type"]
        assert row["action"]
        assert row["occurred_at"]
        assert row["affected_artifact"]
        assert row["result"]
        assert row["reason"]


def test_audit_events_are_queryable_per_run_id(conn):
    run_a = create_run(conn, requirement_input="a", scenario_type="greenfield", policy_pack_version="1.0.0")
    run_b = create_run(conn, requirement_input="b", scenario_type="brownfield", policy_pack_version="1.0.0")
    rows_a = conn.execute("SELECT run_id FROM audit_events WHERE run_id = ?", (run_a,)).fetchall()
    rows_b = conn.execute("SELECT run_id FROM audit_events WHERE run_id = ?", (run_b,)).fetchall()
    assert all(r["run_id"] == run_a for r in rows_a)
    assert all(r["run_id"] == run_b for r in rows_b)
    assert len(rows_a) >= 1 and len(rows_b) >= 1
