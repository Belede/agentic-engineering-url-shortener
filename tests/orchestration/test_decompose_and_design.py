"""T019/T020: DECOMPOSE and DESIGN nodes. FR-011, FR-014, FR-015."""
from pathlib import Path

import pytest

from orchestration.engine import create_run, get_run, transition
from orchestration.nodes.decompose import run_decompose
from orchestration.nodes.design import run_design
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "decompose.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


@pytest.fixture
def run_at_decompose(conn):
    run_id = create_run(conn, requirement_input="Add batch create", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalized")
    transition(conn, run_id, to_state="DECOMPOSE", actor="system", reason="quality checks passed")
    return run_id


def test_run_decompose_records_decision_and_transitions_to_design(conn, run_at_decompose):
    run_decompose(conn, run_at_decompose, summary="Task: add POST /links/batch endpoint")
    assert get_run(conn, run_at_decompose)["current_state"] == "DESIGN"
    row = conn.execute(
        "SELECT decision_type, content FROM decisions WHERE run_id = ? ORDER BY id DESC LIMIT 1",
        (run_at_decompose,),
    ).fetchone()
    assert row["decision_type"] == "decomposition"
    assert "batch" in row["content"]


def test_run_design_records_decision_and_transitions_to_arch_approval(conn, run_at_decompose):
    run_decompose(conn, run_at_decompose, summary="Task: add POST /links/batch endpoint")
    run_design(conn, run_at_decompose, summary="Additive endpoint, contract 1.0.0->1.1.0", security_sensitive=False)
    assert get_run(conn, run_at_decompose)["current_state"] == "ARCH_APPROVAL"
    row = conn.execute(
        "SELECT decision_type, content FROM decisions WHERE run_id = ? ORDER BY id DESC LIMIT 1",
        (run_at_decompose,),
    ).fetchone()
    assert row["decision_type"] == "design"


def test_run_design_records_security_sensitive_flag_on_run(conn, run_at_decompose):
    run_decompose(conn, run_at_decompose, summary="Touches config.py for default TTL")
    run_design(conn, run_at_decompose, summary="Adds SHORTENER_DEFAULT_TTL_DAYS", security_sensitive=True)
    row = conn.execute(
        "SELECT security_sensitive FROM workflow_runs WHERE run_id = ?", (run_at_decompose,)
    ).fetchone()
    assert row["security_sensitive"] == 1
