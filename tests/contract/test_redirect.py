"""T012: GET /{code} redirect + expiry. FR-004, FR-005."""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from shortener.api.app import create_app
from shortener.persistence import api_keys_repository
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner


@pytest.fixture
def client_and_conn(tmp_path):
    db_path = str(tmp_path / "redirect.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="caller 1")
    conn.close()
    return TestClient(app), db_path


def test_redirect_to_valid_code_returns_302(client_and_conn):
    client, _ = client_and_conn
    create_resp = client.post(
        "/api/v1/links", json={"target_url": "https://example.com/target"},
        headers={"X-API-Key": "k1"},
    )
    code = create_resp.json()["code"]
    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/target"


def test_redirect_to_unknown_code_returns_404(client_and_conn):
    client, _ = client_and_conn
    resp = client.get("/doesnotexist", follow_redirects=False)
    assert resp.status_code == 404


def test_redirect_to_expired_code_returns_410(client_and_conn):
    client, _ = client_and_conn
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    create_resp = client.post(
        "/api/v1/links",
        json={"target_url": "https://example.com/target", "expires_at": past},
        headers={"X-API-Key": "k1"},
    )
    code = create_resp.json()["code"]
    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 410
