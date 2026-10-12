"""T026: RELEASE_APPROVAL node + release API, three-way outcome. FR-020, NFR-011."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orchestration.engine import create_run, transition
from shortener.api.app import create_app
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def api(tmp_path):
    db_path = str(tmp_path / "release.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    conn.close()
    return TestClient(app), db_path


def _run_to_release_approval(db_path):
    conn = get_connection(db_path)
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    for to_state, actor in [
        ("QUALITY_CHECK", "system"), ("DECOMPOSE", "system"), ("DESIGN", "system"),
        ("ARCH_APPROVAL", "system"), ("IMPLEMENT", "human"), ("TEST", "system"),
        ("DOCUMENT", "system"), ("RELEASE_APPROVAL", "system"),
    ]:
        transition(conn, run_id, to_state=to_state, actor=actor, reason="x")
    conn.close()
    return run_id


@pytest.mark.parametrize("decision", ["READY", "READY_WITH_LIMITATIONS"])
def test_ready_decisions_transition_to_done(api, decision):
    client, db_path = api
    run_id = _run_to_release_approval(db_path)
    resp = client.post(
        f"/api/v1/workflows/{run_id}/release",
        json={"decision": decision, "decided_by": "belede", "rationale": "all checks pass"},
    )
    assert resp.status_code == 200
    assert resp.json()["current_state"] == "DONE"


def test_not_ready_decision_transitions_to_safe_stop(api):
    client, db_path = api
    run_id = _run_to_release_approval(db_path)
    resp = client.post(
        f"/api/v1/workflows/{run_id}/release",
        json={"decision": "NOT_READY", "decided_by": "belede", "rationale": "mandatory check failed"},
    )
    assert resp.json()["current_state"] == "SAFE_STOP"


def test_invalid_decision_value_rejected(api):
    client, db_path = api
    run_id = _run_to_release_approval(db_path)
    resp = client.post(
        f"/api/v1/workflows/{run_id}/release",
        json={"decision": "MAYBE", "decided_by": "belede", "rationale": "x"},
    )
    assert resp.status_code == 400


def test_release_decision_persisted_in_approval_records(api):
    client, db_path = api
    run_id = _run_to_release_approval(db_path)
    client.post(
        f"/api/v1/workflows/{run_id}/release",
        json={"decision": "READY", "decided_by": "belede", "rationale": "all evidence present"},
    )
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT gate, decision FROM approval_records WHERE run_id = ? AND gate = 'RELEASE_APPROVAL'",
        (run_id,),
    ).fetchone()
    conn.close()
    assert row["decision"] == "READY"


def test_terminal_status_set_on_done(api):
    client, db_path = api
    run_id = _run_to_release_approval(db_path)
    client.post(
        f"/api/v1/workflows/{run_id}/release",
        json={"decision": "READY", "decided_by": "belede", "rationale": "x"},
    )
    conn = get_connection(db_path)
    row = conn.execute("SELECT terminal_status FROM workflow_runs WHERE run_id = ?", (run_id,)).fetchone()
    conn.close()
    assert row["terminal_status"] == "DONE"
