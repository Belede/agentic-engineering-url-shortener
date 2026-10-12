"""Explicit, hand-written SQL migration runner. ADR-002.

Migrations are plain .sql files named `<version>.sql` with an optional
`<version>.down.sql` reversal script. Applied versions are tracked in a
`schema_migrations` table so apply_all() is idempotent (re-running does not
re-apply already-applied migrations) — required for FR-019 (safe resume).
"""
import sqlite3
from pathlib import Path


class MigrationRunner:
    def __init__(self, conn: sqlite3.Connection, migrations_dir: Path):
        self._conn = conn
        self._dir = Path(migrations_dir)
        self._ensure_tracking_table()

    def _ensure_tracking_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        self._conn.commit()

    def _applied_versions(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        return [r[0] for r in rows]

    def _available_versions(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("*.sql") if not p.name.endswith(".down.sql"))

    def current_version(self) -> str | None:
        applied = self._applied_versions()
        return applied[-1] if applied else None

    def apply_all(self) -> None:
        applied = set(self._applied_versions())
        for version in self._available_versions():
            if version in applied:
                continue
            sql_path = self._dir / f"{version}.sql"
            self._conn.executescript(sql_path.read_text())
            self._conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)", (version,)
            )
            self._conn.commit()

    def rollback_last(self) -> None:
        version = self.current_version()
        if version is None:
            return
        down_path = self._dir / f"{version}.down.sql"
        if not down_path.exists():
            raise FileNotFoundError(f"No down script for migration {version}")
        self._conn.executescript(down_path.read_text())
        self._conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
        self._conn.commit()
