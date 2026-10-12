"""T014: persistence-failure handling — fail safe, no partial write. FR-010."""
import os
import stat

import pytest
from fastapi.testclient import TestClient

from shortener.api.app import create_app
from shortener.persistence import api_keys_repository
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner


@pytest.fixture
def readonly_db_client(tmp_path):
    db_path = str(tmp_path / "ro.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="caller 1")
    conn.close()

    # Make the DB file (and its directory, since SQLite needs to create
    # -wal/-journal siblings) unwritable to force a genuine persistence failure.
    os.chmod(db_path, stat.S_IREAD)
    os.chmod(tmp_path, stat.S_IREAD | stat.S_IEXEC)

    yield TestClient(app), db_path

    # Restore permissions so pytest's tmp_path cleanup can remove the dir.
    os.chmod(tmp_path, stat.S_IRWXU)
    os.chmod(db_path, stat.S_IRWXU)


def test_create_link_returns_503_when_db_unwritable(readonly_db_client):
    client, _ = readonly_db_client
    resp = client.post(
        "/api/v1/links", json={"target_url": "https://example.com"},
        headers={"X-API-Key": "k1"},
    )
    assert resp.status_code == 503
