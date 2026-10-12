"""Shared FastAPI dependencies: DB connection per request, migrations applied."""
from collections.abc import Generator

from fastapi import Request

from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner


def get_db(request: Request) -> Generator:
    conn = get_connection(request.app.state.db_path)
    MigrationRunner(conn, request.app.state.migrations_dir).apply_all()
    try:
        yield conn
    finally:
        conn.close()
