"""T003: DB connection + migration runner. FR-011 (persisted state), ADR-002."""
import sqlite3
import textwrap

import pytest

from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner


@pytest.fixture
def migrations_dir(tmp_path):
    d = tmp_path / "migrations"
    d.mkdir()
    (d / "0001_test.sql").write_text(
        textwrap.dedent("""\
            CREATE TABLE widgets (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        """)
    )
    (d / "0001_test.down.sql").write_text("DROP TABLE widgets;")
    return d


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "test.db"))
    yield c
    c.close()


def test_get_connection_enables_wal_and_foreign_keys(conn):
    mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert mode.lower() == "wal"
    fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    assert fk == 1


def test_apply_all_creates_schema_migrations_table(conn, migrations_dir):
    runner = MigrationRunner(conn, migrations_dir)
    runner.apply_all()
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    assert [r[0] for r in rows] == ["0001_test"]


def test_apply_all_actually_runs_the_migration_sql(conn, migrations_dir):
    runner = MigrationRunner(conn, migrations_dir)
    runner.apply_all()
    conn.execute("INSERT INTO widgets (name) VALUES ('a')")
    assert conn.execute("SELECT COUNT(*) FROM widgets").fetchone()[0] == 1


def test_apply_all_is_idempotent(conn, migrations_dir):
    runner = MigrationRunner(conn, migrations_dir)
    runner.apply_all()
    runner.apply_all()  # must not re-run / must not error on duplicate table
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    assert len(rows) == 1


def test_current_version_reflects_latest_applied(conn, migrations_dir):
    runner = MigrationRunner(conn, migrations_dir)
    assert runner.current_version() is None
    runner.apply_all()
    assert runner.current_version() == "0001_test"


def test_rollback_last_runs_down_script_and_removes_record(conn, migrations_dir):
    runner = MigrationRunner(conn, migrations_dir)
    runner.apply_all()
    runner.rollback_last()
    assert runner.current_version() is None
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("SELECT * FROM widgets")


def test_up_down_up_cycle_leaves_schema_in_applied_state(conn, migrations_dir):
    """Required evidence for brownfield migration reversibility (ADR-002)."""
    runner = MigrationRunner(conn, migrations_dir)
    runner.apply_all()
    runner.rollback_last()
    runner.apply_all()
    assert runner.current_version() == "0001_test"
    conn.execute("INSERT INTO widgets (name) VALUES ('b')")
    assert conn.execute("SELECT COUNT(*) FROM widgets").fetchone()[0] == 1
