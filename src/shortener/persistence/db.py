"""DB connection factory. ADR-002: SQLite, single file, WAL mode for writer concurrency."""
import sqlite3


def get_connection(path: str) -> sqlite3.Connection:
    """Open a SQLite connection with WAL journal mode and foreign keys enabled.

    WAL mode reduces (but does not eliminate) writer contention under the
    concurrency tests this prototype relies on (FR-008, FR-030) — the
    single-writer limitation remains and is documented in
    docs/governance/known-limitations.md.
    """
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn
