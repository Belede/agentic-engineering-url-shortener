"""T039/T040: Brownfield scenario — optional max_clicks limit. CL-02.

Migration 0002 (reversible), atomic conditional UPDATE for concurrency-safe
click counting, 410 LINK_EXHAUSTED outcome.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shortener.api.app import create_app
from shortener.persistence import api_keys_repository
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


# --- T039: migration 0002 up/down/up -----------------------------------

@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "brownfield_migration.db"))
    yield c
    c.close()


def test_0002_adds_max_clicks_column(conn):
    runner = MigrationRunner(conn, MIGRATIONS_DIR)
    runner.apply_all()
    assert runner.current_version() == "0002_max_clicks"
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(short_links)").fetchall()}
    assert "max_clicks" in columns


def test_0002_up_down_up_cycle_preserves_existing_rows(conn):
    runner = MigrationRunner(conn, MIGRATIONS_DIR)
    runner.apply_all()
    conn.execute(
        "INSERT INTO api_keys (key_id, label) VALUES ('k', 'test')"
    )
    conn.execute(
        "INSERT INTO short_links (code, target_url, created_by) VALUES ('abc1234', 'https://x.com', 'k')"
    )
    conn.commit()

    runner.rollback_last()
    columns_after_down = {r["name"] for r in conn.execute("PRAGMA table_info(short_links)").fetchall()}
    assert "max_clicks" not in columns_after_down
    # existing row survives the column drop
    assert conn.execute("SELECT COUNT(*) FROM short_links WHERE code='abc1234'").fetchone()[0] == 1

    runner.apply_all()
    columns_after_up_again = {r["name"] for r in conn.execute("PRAGMA table_info(short_links)").fetchall()}
    assert "max_clicks" in columns_after_up_again
    row = conn.execute("SELECT max_clicks FROM short_links WHERE code='abc1234'").fetchone()
    assert row["max_clicks"] is None  # existing link: unlimited, unaffected (regression requirement)


# --- T040: atomic max_clicks enforcement --------------------------------

@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "brownfield_app.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="caller 1")
    conn.close()
    return TestClient(app), db_path


def test_link_without_max_clicks_is_unaffected_regression(client):
    """Regression requirement from the impact analysis: existing/unlimited
    links must behave exactly as before this change."""
    c, _ = client
    code = c.post(
        "/api/v1/links", json={"target_url": "https://example.com"}, headers={"X-API-Key": "k1"}
    ).json()["code"]
    for _ in range(5):
        resp = c.get(f"/{code}", follow_redirects=False)
        assert resp.status_code == 302


def test_link_with_max_clicks_returns_410_once_exhausted(client):
    c, _ = client
    code = c.post(
        "/api/v1/links", json={"target_url": "https://example.com", "max_clicks": 2},
        headers={"X-API-Key": "k1"},
    ).json()["code"]

    assert c.get(f"/{code}", follow_redirects=False).status_code == 302
    assert c.get(f"/{code}", follow_redirects=False).status_code == 302
    exhausted_resp = c.get(f"/{code}", follow_redirects=False)
    assert exhausted_resp.status_code == 410
    assert exhausted_resp.json()["error"] == "LINK_EXHAUSTED"


def test_concurrent_redirects_never_exceed_max_clicks(client):
    """The actual concurrency-safety evidence the impact analysis called for:
    N=20 parallel requests against a link with max_clicks=5 must result in
    EXACTLY 5 successful redirects, never more."""
    from concurrent.futures import ThreadPoolExecutor

    c, _db_path = client
    code = c.post(
        "/api/v1/links", json={"target_url": "https://example.com", "max_clicks": 5},
        headers={"X-API-Key": "k1"},
    ).json()["code"]

    def hit():
        return c.get(f"/{code}", follow_redirects=False).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda _: hit(), range(20)))

    successes = results.count(302)
    exhausted = results.count(410)
    assert successes == 5  # never exceeds the limit, even under concurrency
    assert exhausted == 15
    assert successes + exhausted == 20
