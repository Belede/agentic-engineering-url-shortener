"""T023: IMPLEMENT node. constitution Principle IV (human-supervised execution record)."""
from pathlib import Path

import pytest

from orchestration.engine import create_run, get_run
from orchestration.nodes.implement import run_implement
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "impl.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


def test_run_implement_records_summary_and_transitions_to_test(conn):
    from orchestration.engine import transition
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="x")
    transition(conn, run_id, to_state="DECOMPOSE", actor="system", reason="x")
    transition(conn, run_id, to_state="DESIGN", actor="system", reason="x")
    transition(conn, run_id, to_state="ARCH_APPROVAL", actor="system", reason="x")
    transition(conn, run_id, to_state="IMPLEMENT", actor="human", reason="approved")

    run_implement(conn, run_id, summary="Added POST /links/batch, 3 files changed")

    assert get_run(conn, run_id)["current_state"] == "TEST"
    row = conn.execute(
        "SELECT action, result FROM audit_events WHERE run_id = ? AND action = 'implementation_recorded'",
        (run_id,),
    ).fetchone()
    assert row is not None
