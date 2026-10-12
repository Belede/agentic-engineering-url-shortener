"""Health/readiness endpoints. FR-021: distinguish process-up from deps-healthy."""
import sqlite3

from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict:
    """Process liveness only — no dependency check."""
    return {"status": "up"}


@router.get("/readyz")
def readyz(request: Request, response: Response) -> dict:
    """Dependency readiness — DB must actually be reachable."""
    db_path = request.app.state.db_path
    try:
        conn = sqlite3.connect(db_path, timeout=1)
        conn.execute("SELECT 1")
        conn.close()
    except sqlite3.OperationalError:
        response.status_code = 503
        return {"status": "not ready", "reason": "database unreachable"}
    return {"status": "ready"}
