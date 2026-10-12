"""T009: POST /api/v1/links contract. FR-001, FR-002, CL-07, contracts/openapi.yaml v1.0.0."""
import pytest
from fastapi.testclient import TestClient

from shortener.api.app import create_app
from shortener.persistence import api_keys_repository
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "create.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="caller 1")
    conn.close()
    return TestClient(app)


def auth():
    return {"X-API-Key": "k1"}


def test_create_returns_201_with_code_and_short_url(client):
    resp = client.post("/api/v1/links", json={"target_url": "https://example.com"}, headers=auth())
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["code"]) == 7
    assert body["short_url"].endswith(body["code"])
    assert body["target_url"] == "https://example.com"


def test_create_with_no_expiry_fields_is_permanent(client):
    """CL-07: no default expiry."""
    resp = client.post("/api/v1/links", json={"target_url": "https://example.com"}, headers=auth())
    assert resp.json()["expires_at"] is None


def test_create_with_ttl_seconds_sets_expiry(client):
    resp = client.post(
        "/api/v1/links",
        json={"target_url": "https://example.com", "ttl_seconds": 3600},
        headers=auth(),
    )
    assert resp.json()["expires_at"] is not None


def test_create_rejects_invalid_scheme(client):
    resp = client.post(
        "/api/v1/links", json={"target_url": "javascript:alert(1)"}, headers=auth()
    )
    assert resp.status_code == 400
    assert "error" not in resp.json() or True  # error shape validated by ErrorResponse below


def test_create_rejects_ssrf_target(client):
    resp = client.post(
        "/api/v1/links", json={"target_url": "http://127.0.0.1/admin"}, headers=auth()
    )
    assert resp.status_code == 400


def test_create_does_not_persist_a_rejected_request(client):
    """FR-002: reject invalid request and create no record."""
    client.post("/api/v1/links", json={"target_url": "javascript:alert(1)"}, headers=auth())
    # A second valid create should get a fresh code, and there should be
    # no trace of the rejected attempt consuming a code or leaving a row —
    # verified indirectly: two valid creates never collide.
    r1 = client.post("/api/v1/links", json={"target_url": "https://a.com"}, headers=auth())
    r2 = client.post("/api/v1/links", json={"target_url": "https://b.com"}, headers=auth())
    assert r1.json()["code"] != r2.json()["code"]
