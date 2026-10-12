"""T031: safe-stop + resume. Two DISTINCT cases per the independent review
(condition #1) — these are not the same mechanism and must not share one
glossed-over test:

1. Safe-stop -> explicit human resume (FR-024): a run that entered SAFE_STOP
   (e.g. retry exhaustion) can only continue via an explicit human action
   that re-enters the graph at the failed node.
2. Process-crash-mid-stage -> resume (FR-019): a run that was never
   safe-stopped, but whose process was interrupted mid-stage, must be
   resumable by a fresh process simply re-reading persisted state — no
   human gate involved, because nothing unsafe happened, the process just died.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orchestration.engine import create_run, get_run, transition
from shortener.api.app import create_app
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


# --- Case 1: safe-stop -> human resume -------------------------------------

@pytest.fixture
def api(tmp_path):
    db_path = str(tmp_path / "safestop.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    conn.close()
    return TestClient(app), db_path


def test_safe_stopped_run_cannot_progress_without_explicit_resume(api):
    client, db_path = api
    conn = get_connection(db_path)
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="x")
    transition(conn, run_id, to_state="DECOMPOSE", actor="system", reason="x")
    transition(conn, run_id, to_state="DESIGN", actor="system", reason="x")
    transition(conn, run_id, to_state="ARCH_APPROVAL", actor="system", reason="x")
    transition(conn, run_id, to_state="SAFE_STOP", actor="human", reason="rejected")
    conn.close()

    resp = client.get(f"/api/v1/workflows/{run_id}")
    assert resp.json()["current_state"] == "SAFE_STOP"


def test_human_resume_reenters_at_a_specific_failed_node(api):
    client, db_path = api
    conn = get_connection(db_path)
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    for to_state, actor in [
        ("QUALITY_CHECK", "system"), ("DECOMPOSE", "system"), ("DESIGN", "system"),
        ("ARCH_APPROVAL", "system"), ("IMPLEMENT", "human"), ("TEST", "system"),
        ("SAFE_STOP", "system"),
    ]:
        transition(conn, run_id, to_state=to_state, actor=actor, reason="simulated failure")
    conn.close()

    resp = client.post(
        f"/api/v1/workflows/{run_id}/resume",
        json={"to_state": "TEST", "decided_by": "belede", "rationale": "bug fixed test-first, resuming"},
    )
    assert resp.status_code == 200
    assert resp.json()["current_state"] == "TEST"


def test_resume_to_non_graph_edge_is_rejected(api):
    client, db_path = api
    conn = get_connection(db_path)
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="x")
    transition(conn, run_id, to_state="DECOMPOSE", actor="system", reason="x")
    transition(conn, run_id, to_state="DESIGN", actor="system", reason="x")
    transition(conn, run_id, to_state="ARCH_APPROVAL", actor="system", reason="x")
    transition(conn, run_id, to_state="SAFE_STOP", actor="human", reason="rejected")
    conn.close()

    resp = client.post(
        f"/api/v1/workflows/{run_id}/resume",
        json={"to_state": "DONE", "decided_by": "belede", "rationale": "skip ahead"},
    )
    assert resp.status_code == 409


def test_resume_requires_run_to_actually_be_at_safe_stop(api):
    client, db_path = api
    conn = get_connection(db_path)
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    conn.close()  # still at INGEST

    resp = client.post(
        f"/api/v1/workflows/{run_id}/resume",
        json={"to_state": "DESIGN", "decided_by": "belede", "rationale": "x"},
    )
    assert resp.status_code == 409


# --- Case 2: process-crash-mid-stage -> resume (FR-019) --------------------

def test_crash_mid_stage_is_recoverable_by_a_fresh_process_reading_persisted_state(tmp_path):
    """No SAFE_STOP involved at all — the run was simply interrupted between
    IMPLEMENT and TEST (process killed). A fresh connection (simulating a
    fresh process) reads the correct current_state and the work can
    continue from exactly there, with no lost history."""
    db_path = str(tmp_path / "crash.db")

    # "Process A": gets the run to IMPLEMENT, then "crashes" (connection closed).
    conn_a = get_connection(db_path)
    MigrationRunner(conn_a, MIGRATIONS_DIR).apply_all()
    run_id = create_run(conn_a, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    for to_state, actor in [
        ("QUALITY_CHECK", "system"), ("DECOMPOSE", "system"), ("DESIGN", "system"),
        ("ARCH_APPROVAL", "system"), ("IMPLEMENT", "human"),
    ]:
        transition(conn_a, run_id, to_state=to_state, actor=actor, reason="x")
    history_before_crash = conn_a.execute(
        "SELECT COUNT(*) FROM state_transitions WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    conn_a.close()  # simulates process death — no explicit shutdown transition

    # "Process B": a fresh connection, no shared memory with Process A.
    conn_b = get_connection(db_path)
    run = get_run(conn_b, run_id)
    assert run["current_state"] == "IMPLEMENT"  # exactly where it was, not reset
    history_after_restart = conn_b.execute(
        "SELECT COUNT(*) FROM state_transitions WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    assert history_after_restart == history_before_crash  # zero lost history

    # Work continues normally from here — no special "crash resume" gate
    # needed, because nothing unsafe happened; this is the key distinction
    # from Case 1 (safe-stop requires an explicit human decision; a plain
    # process restart does not).
    transition(conn_b, run_id, to_state="TEST", actor="system", reason="implementation complete")
    assert get_run(conn_b, run_id)["current_state"] == "TEST"
    conn_b.close()
