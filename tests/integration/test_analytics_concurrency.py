"""T013: atomic analytics write, consistent under concurrency. FR-006, FR-008, NFR-003."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from shortener.api.app import create_app
from shortener.persistence import api_keys_repository
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner


@pytest.fixture
def client_and_code(tmp_path):
    db_path = str(tmp_path / "analytics.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="caller 1")
    conn.close()
    client = TestClient(app)
    code = client.post(
        "/api/v1/links", json={"target_url": "https://example.com"},
        headers={"X-API-Key": "k1"},
    ).json()["code"]
    return client, code, db_path


def test_single_redirect_records_exactly_one_event(client_and_code):
    client, code, db_path = client_and_code
    client.get(f"/{code}", follow_redirects=False)
    conn = get_connection(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM redirect_events WHERE code = ?", (code,)
    ).fetchone()[0]
    conn.close()
    assert count == 1


def test_concurrent_redirects_record_exactly_one_event_each(client_and_code):
    """FR-008: correctness under concurrent requests — no lost/double events."""
    client, code, db_path = client_and_code
    n = 20

    def hit():
        return client.get(f"/{code}", follow_redirects=False).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda _: hit(), range(n)))

    assert all(status == 302 for status in results)
    conn = get_connection(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM redirect_events WHERE code = ?", (code,)
    ).fetchone()[0]
    conn.close()
    assert count == n
