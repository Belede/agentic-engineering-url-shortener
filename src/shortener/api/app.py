"""FastAPI application factory. ADR-001: single-process modular monolith,
logical plane separation between application (shortener) and orchestration."""
from pathlib import Path

from fastapi import FastAPI

from shortener.api.health import router as health_router

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

    app.include_router(health_router)

    return app


app = create_app()
