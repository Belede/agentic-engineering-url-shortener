"""T010: Idempotency-Key handling. FR-007, CL-04."""
import pytest
from fastapi.testclient import TestClient

from shortener.api.app import create_app
from shortener.persistence import api_keys_repository
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "idem.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="caller 1")
    api_keys_repository.create_key(conn, key_id="k2", label="caller 2")
    conn.close()
    return TestClient(app)


def test_repeated_idempotency_key_returns_original_result(client):
    headers = {"X-API-Key": "k1", "Idempotency-Key": "req-123"}
    r1 = client.post("/api/v1/links", json={"target_url": "https://example.com/a"}, headers=headers)
    r2 = client.post("/api/v1/links", json={"target_url": "https://example.com/a"}, headers=headers)
    assert r1.json()["code"] == r2.json()["code"]


def test_different_idempotency_keys_create_separate_links(client):
    r1 = client.post(
        "/api/v1/links", json={"target_url": "https://example.com/a"},
        headers={"X-API-Key": "k1", "Idempotency-Key": "req-1"},
    )
    r2 = client.post(
        "/api/v1/links", json={"target_url": "https://example.com/a"},
        headers={"X-API-Key": "k1", "Idempotency-Key": "req-2"},
    )
    assert r1.json()["code"] != r2.json()["code"]


def test_idempotency_key_is_scoped_per_caller(client):
    """Same key, different callers — must not collide (CL-04 scopes by caller)."""
    r1 = client.post(
        "/api/v1/links", json={"target_url": "https://example.com/a"},
        headers={"X-API-Key": "k1", "Idempotency-Key": "shared-key"},
    )
    r2 = client.post(
        "/api/v1/links", json={"target_url": "https://example.com/a"},
        headers={"X-API-Key": "k2", "Idempotency-Key": "shared-key"},
    )
    assert r1.json()["code"] != r2.json()["code"]


def test_no_idempotency_key_creates_separate_links_each_time(client):
    headers = {"X-API-Key": "k1"}
    r1 = client.post("/api/v1/links", json={"target_url": "https://example.com/a"}, headers=headers)
    r2 = client.post("/api/v1/links", json={"target_url": "https://example.com/a"}, headers=headers)
    assert r1.json()["code"] != r2.json()["code"]
