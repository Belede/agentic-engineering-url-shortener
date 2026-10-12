"""T021: ARCH_APPROVAL node + approve/reject API. FR-013, NFR-011, ADR-005."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orchestration.engine import create_run, transition
from orchestration.nodes.decompose import run_decompose
from orchestration.nodes.design import run_design
from shortener.api.app import create_app
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def api(tmp_path):
    db_path = str(tmp_path / "arch.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    conn.close()
    return TestClient(app), db_path


def _run_to_arch_approval(db_path, security_sensitive=False):
    conn = get_connection(db_path)
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalized")
    transition(conn, run_id, to_state="DECOMPOSE", actor="system", reason="checks passed")
    run_decompose(conn, run_id, summary="tasks")
    run_design(conn, run_id, summary="design", security_sensitive=security_sensitive)
    conn.close()
    return run_id


def test_approve_without_security_sensitivity_goes_straight_to_implement(api):
    client, db_path = api
    run_id = _run_to_arch_approval(db_path, security_sensitive=False)
    resp = client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"gate": "ARCH_APPROVAL", "decision": "approved", "decided_by": "belede", "rationale": "looks good"},
    )
    assert resp.status_code == 200
    assert resp.json()["current_state"] == "IMPLEMENT"


def test_approve_with_security_sensitivity_routes_to_security_approval(api):
    client, db_path = api
    run_id = _run_to_arch_approval(db_path, security_sensitive=True)
    resp = client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"gate": "ARCH_APPROVAL", "decision": "approved", "decided_by": "belede", "rationale": "ok, touches config"},
    )
    assert resp.json()["current_state"] == "SECURITY_APPROVAL"


def test_reject_routes_to_safe_stop(api):
    client, db_path = api
    run_id = _run_to_arch_approval(db_path)
    resp = client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"gate": "ARCH_APPROVAL", "decision": "rejected", "decided_by": "belede", "rationale": "not acceptable"},
    )
    assert resp.json()["current_state"] == "SAFE_STOP"


def test_approval_record_is_persisted(api):
    client, db_path = api
    run_id = _run_to_arch_approval(db_path)
    client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"gate": "ARCH_APPROVAL", "decision": "approved", "decided_by": "belede", "rationale": "ok"},
    )
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT gate, decision, decided_by, rationale FROM approval_records WHERE run_id = ?", (run_id,)
    ).fetchone()
    conn.close()
    assert row["gate"] == "ARCH_APPROVAL"
    assert row["decision"] == "approved"
    assert row["decided_by"] == "belede"


def test_approve_wrong_gate_for_current_state_rejected(api):
    client, db_path = api
    run_id = _run_to_arch_approval(db_path)
    resp = client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"gate": "RELEASE_APPROVAL", "decision": "approved", "decided_by": "belede", "rationale": "x"},
    )
    assert resp.status_code == 409


def test_security_approval_gate_approve_goes_to_implement(api):
    client, db_path = api
    run_id = _run_to_arch_approval(db_path, security_sensitive=True)
    client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"gate": "ARCH_APPROVAL", "decision": "approved", "decided_by": "belede", "rationale": "ok"},
    )
    resp = client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"gate": "SECURITY_APPROVAL", "decision": "approved", "decided_by": "belede", "rationale": "security reviewed"},
    )
    assert resp.json()["current_state"] == "IMPLEMENT"


def test_security_approval_gate_reject_goes_to_safe_stop(api):
    client, db_path = api
    run_id = _run_to_arch_approval(db_path, security_sensitive=True)
    client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"gate": "ARCH_APPROVAL", "decision": "approved", "decided_by": "belede", "rationale": "ok"},
    )
    resp = client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"gate": "SECURITY_APPROVAL", "decision": "rejected", "decided_by": "belede", "rationale": "insufficient review"},
    )
    assert resp.json()["current_state"] == "SAFE_STOP"
