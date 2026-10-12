"""T005: FastAPI skeleton health/readiness. FR-021, ADR-001."""
from fastapi.testclient import TestClient

from shortener.api.app import create_app


def test_healthz_returns_200_without_db():
    app = create_app(db_path=":memory:")
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200


def test_readyz_returns_200_when_db_reachable(tmp_path):
    app = create_app(db_path=str(tmp_path / "ready.db"))
    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code == 200


def test_readyz_returns_503_when_db_unreachable():
    # An unwritable path makes the DB genuinely unreachable at connect time.
    app = create_app(db_path="/nonexistent-dir-xyz/unreachable.db")
    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code == 503
