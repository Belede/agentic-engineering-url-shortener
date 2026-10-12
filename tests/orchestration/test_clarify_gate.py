"""T018: CLARIFY node + human clarification API. FR-013, FR-017, NFR-011, ADR-005."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orchestration.engine import create_run, get_run, transition
from shortener.api.app import create_app
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "clarify.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


@pytest.fixture
def api(tmp_path):
    db_path = str(tmp_path / "clarify_api.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    conn.close()
    return TestClient(app), db_path


def _run_to_clarify(conn, run_id):
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalized")
    transition(conn, run_id, to_state="CLARIFY", actor="system", reason="ambiguity detected")


def test_run_parked_at_clarify_never_auto_advances(conn):
    run_id = create_run(conn, requirement_input="x", scenario_type="ambiguous", policy_pack_version="1.0.0")
    _run_to_clarify(conn, run_id)
    assert get_run(conn, run_id)["current_state"] == "CLARIFY"
    # No system action, no timeout — simulate time passing: nothing happens.
    assert get_run(conn, run_id)["current_state"] == "CLARIFY"


def test_api_requires_decided_by_and_answer(api):
    client, db_path = api
    conn = get_connection(db_path)
    run_id = create_run(conn, requirement_input="x", scenario_type="ambiguous", policy_pack_version="1.0.0")
    _run_to_clarify(conn, run_id)
    conn.close()

    resp = client.post(f"/api/v1/workflows/{run_id}/clarify", json={})
    assert resp.status_code == 422  # missing required fields


def test_api_clarify_answer_records_decision_and_resumes(api):
    client, db_path = api
    conn = get_connection(db_path)
    run_id = create_run(conn, requirement_input="x", scenario_type="ambiguous", policy_pack_version="1.0.0")
    _run_to_clarify(conn, run_id)
    conn.close()

    resp = client.post(
        f"/api/v1/workflows/{run_id}/clarify",
        json={"answer": "New links only", "decided_by": "belede", "rationale": "existing links must not break"},
    )
    assert resp.status_code == 200
    assert resp.json()["current_state"] == "RENORMALIZE"

    conn = get_connection(db_path)
    decision = conn.execute(
        "SELECT decision_type, content FROM decisions WHERE run_id = ?", (run_id,)
    ).fetchone()
    conn.close()
    assert decision["decision_type"] == "clarification"
    assert "New links only" in decision["content"]


def test_api_rejects_clarify_on_run_not_at_clarify_gate(api):
    client, db_path = api
    conn = get_connection(db_path)
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    conn.close()  # still at INGEST, not CLARIFY

    resp = client.post(
        f"/api/v1/workflows/{run_id}/clarify",
        json={"answer": "x", "decided_by": "belede", "rationale": "x"},
    )
    assert resp.status_code == 409
