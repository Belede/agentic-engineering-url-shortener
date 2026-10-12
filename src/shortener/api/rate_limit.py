"""In-process rate limiter: fixed window, 60 req/min per API key (FR-028, CL-08).

State lives on app.state (per-process) — acceptable for a single-process
prototype (ADR-001); a multi-process deployment would need a shared store,
documented as a known limitation.
"""
import time

from fastapi import Depends, HTTPException, Request

from shortener.api.auth import require_api_key

WINDOW_SECONDS = 60


class RateLimiter:
    def __init__(self, limit_per_minute: int = 60):
        self.limit = limit_per_minute
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - WINDOW_SECONDS
        hits = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(hits) >= self.limit:
            self._hits[key] = hits
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        hits.append(now)
        self._hits[key] = hits


def get_rate_limiter(request: Request) -> RateLimiter:
    if not hasattr(request.app.state, "rate_limiter"):
        request.app.state.rate_limiter = RateLimiter(
            limit_per_minute=getattr(request.app.state, "rate_limit_per_minute", 60)
        )
    return request.app.state.rate_limiter


def enforce_rate_limit(
    request: Request,
    api_key: str = Depends(require_api_key),
) -> str:
    limiter = get_rate_limiter(request)
    limiter.check(api_key)
    return api_key
