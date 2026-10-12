"""T008: API-key auth dependency. CL-06, ADR-011."""
import pytest
from fastapi.testclient import TestClient

from shortener.api.app import create_app
from shortener.persistence import api_keys_repository
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner


@pytest.fixture
def app_and_key(tmp_path):
    db_path = str(tmp_path / "auth.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="demo-key", label="demo caller")
    conn.close()
    return app


def test_missing_api_key_rejected(app_and_key):
    client = TestClient(app_and_key)
    resp = client.post("/api/v1/links", json={"target_url": "https://example.com"})
    assert resp.status_code == 401


def test_unknown_api_key_rejected(app_and_key):
    client = TestClient(app_and_key)
    resp = client.post(
        "/api/v1/links",
        json={"target_url": "https://example.com"},
        headers={"X-API-Key": "not-a-real-key"},
    )
    assert resp.status_code == 401


def test_valid_api_key_accepted(app_and_key):
    client = TestClient(app_and_key)
    resp = client.post(
        "/api/v1/links",
        json={"target_url": "https://example.com"},
        headers={"X-API-Key": "demo-key"},
    )
    assert resp.status_code == 201
