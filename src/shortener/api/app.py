"""FastAPI application factory. ADR-001: single-process modular monolith,
logical plane separation between application (shortener) and orchestration."""
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from orchestration.api import router as orchestration_router
from shortener.api.health import router as health_router
from shortener.api.links import router as links_router
from shortener.api.redirect import router as redirect_router

MIGRATIONS_DIR = Path(__file__).parents[1] / "migrations"


def create_app(db_path: str | None = None) -> FastAPI:
    """Build the FastAPI app. `db_path` override exists for test isolation;
    production/dev use reads from Settings (config.py)."""
    from shortener.config import get_settings

    settings = get_settings()
    resolved_db_path = db_path if db_path is not None else settings.db_path

    app = FastAPI(title="Agentic URL Shortener", version="1.0.0")
    app.state.db_path = resolved_db_path
    app.state.migrations_dir = MIGRATIONS_DIR

    app.state.rate_limit_per_minute = settings.rate_limit_per_minute

    app.include_router(health_router)
    app.include_router(links_router)
    app.include_router(orchestration_router)
    app.include_router(redirect_router)  # catch-all /{code} must be registered last

    @app.exception_handler(sqlite3.OperationalError)
    def _persistence_unavailable(request: Request, exc: sqlite3.OperationalError) -> JSONResponse:
        """FR-010: fail safe (503, no partial write) when persistence is
        unavailable — covers failures raised anywhere in the request
        lifecycle, including inside dependencies (e.g. get_db's connection
        setup), not only inside a route body's own try/except."""
        return JSONResponse(
            status_code=503,
            content={"error": "PERSISTENCE_UNAVAILABLE", "message": "Database is unavailable"},
        )

    return app


app = create_app()
