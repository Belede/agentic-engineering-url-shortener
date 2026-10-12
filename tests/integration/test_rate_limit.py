"""T011: rate limiting, 60/min per API key. FR-028, CL-08."""
import pytest
from fastapi.testclient import TestClient

from shortener.api.app import create_app
from shortener.persistence import api_keys_repository
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "rl.db")
    app = create_app(db_path=db_path)
    app.state.rate_limit_per_minute = 3  # small limit for a fast test
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="caller 1")
    api_keys_repository.create_key(conn, key_id="k2", label="caller 2")
    conn.close()
    return TestClient(app)


def test_requests_within_limit_succeed(client):
    for _ in range(3):
        resp = client.post(
            "/api/v1/links", json={"target_url": "https://example.com"},
            headers={"X-API-Key": "k1"},
        )
        assert resp.status_code == 201


def test_request_over_limit_rejected_with_429(client):
    for _ in range(3):
        client.post(
            "/api/v1/links", json={"target_url": "https://example.com"},
            headers={"X-API-Key": "k1"},
        )
    resp = client.post(
        "/api/v1/links", json={"target_url": "https://example.com"},
        headers={"X-API-Key": "k1"},
    )
    assert resp.status_code == 429


def test_rate_limit_is_scoped_per_api_key(client):
    """Exhausting k1's limit must not affect k2."""
    for _ in range(3):
        client.post(
            "/api/v1/links", json={"target_url": "https://example.com"},
            headers={"X-API-Key": "k1"},
        )
    resp = client.post(
        "/api/v1/links", json={"target_url": "https://example.com"},
        headers={"X-API-Key": "k2"},
    )
    assert resp.status_code == 201
