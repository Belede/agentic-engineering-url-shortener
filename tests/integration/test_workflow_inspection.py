"""T027: workflow inspection API. FR-012."""
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
    db_path = str(tmp_path / "inspect.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    run_id = create_run(conn, requirement_input="add batch create", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalized")
    conn.close()
    return TestClient(app), run_id


def test_get_workflow_returns_current_state_and_history(api):
    client, run_id = api
    resp = client.get(f"/api/v1/workflows/{run_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == run_id
    assert body["current_state"] == "QUALITY_CHECK"
    assert len(body["state_history"]) == 2  # INGEST creation + QUALITY_CHECK


def test_get_unknown_workflow_returns_404(api):
    client, _ = api
    resp = client.get("/api/v1/workflows/does-not-exist")
    assert resp.status_code == 404


def test_create_workflow_endpoint(api):
    client, _ = api
    resp = client.post(
        "/api/v1/workflows",
        json={"requirement": "Add optional max_clicks limit", "scenario_type": "brownfield"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["current_state"] == "INGEST"
    assert "run_id" in body
