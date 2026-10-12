"""T004: migration 0001 baseline schema. FR-011, data-model.md."""
from pathlib import Path

import pytest

from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[3] / "src" / "shortener" / "migrations"

EXPECTED_TABLES = {
    "api_keys", "short_links", "redirect_events", "idempotency_keys",
    "workflow_runs", "state_transitions", "decisions", "approval_records",
    "policy_exceptions", "policy_evaluations", "audit_events",
    "schema_migrations",
}


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "baseline.db"))
    yield c
    c.close()


def test_0001_creates_all_baseline_tables(conn):
    runner = MigrationRunner(conn, MIGRATIONS_DIR)
    runner.apply_all()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {r[0] for r in rows}
    assert EXPECTED_TABLES.issubset(table_names)


def test_full_migration_chain_up_down_up_cycle(conn):
    """Rolls every applied migration all the way back (not just the last
    one — this directory now holds 0001 and 0002, so a full-chain teardown
    is the correct regression check), then reapplies everything."""
    runner = MigrationRunner(conn, MIGRATIONS_DIR)
    runner.apply_all()
    while runner.current_version() is not None:
        runner.rollback_last()
    tables_after_full_teardown = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "short_links" not in tables_after_full_teardown

    runner.apply_all()
    tables_after_up_again = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert EXPECTED_TABLES.issubset(tables_after_up_again)
