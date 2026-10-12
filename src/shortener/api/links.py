"""POST /api/v1/links — create a short link. FR-001, FR-002, FR-007, CL-04, CL-07."""
import sqlite3
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from shortener.api.deps import get_db
from shortener.api.rate_limit import enforce_rate_limit
from shortener.domain.shortcode import CodeSpaceExhaustedError, generate_unique_code
from shortener.domain.validation import InvalidUrlError, SsrfBlockedError, validate_target_url
from shortener.persistence import idempotency_repository, links_repository

router = APIRouter()


class CreateLinkRequest(BaseModel):
    target_url: str
    expires_at: str | None = None
    ttl_seconds: int | None = Field(default=None, gt=0)


class LinkResponse(BaseModel):
    code: str
    short_url: str
    target_url: str
    expires_at: str | None


def _resolve_expires_at(body: CreateLinkRequest) -> str | None:
    """CL-07: no default expiry — permanent unless caller sets one."""
    if body.expires_at:
        return body.expires_at
    if body.ttl_seconds:
        return (
            datetime.now(UTC) + timedelta(seconds=body.ttl_seconds)
        ).isoformat()
    return None


@router.post("/api/v1/links", status_code=201, response_model=LinkResponse)
def create_link(
    body: CreateLinkRequest,
    api_key: str = Depends(enforce_rate_limit),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    conn: sqlite3.Connection = Depends(get_db),
) -> LinkResponse:
    # Idempotency check first (FR-007, CL-04): a repeated key returns the
    # original result rather than creating a duplicate.
    if idempotency_key:
        existing_code = idempotency_repository.find_existing_result(
            conn, idempotency_key, api_key
        )
        if existing_code:
            link = links_repository.get_link(conn, existing_code)
            return _to_response(link)

    try:
        validate_target_url(body.target_url)
    except (InvalidUrlError, SsrfBlockedError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    expires_at = _resolve_expires_at(body)

    try:
        code = generate_unique_code(
            exists=lambda c: links_repository.code_exists(conn, c)
        )
        link = links_repository.create_link(
            conn,
            code=code,
            target_url=body.target_url,
            created_by=api_key,
            expires_at=expires_at,
        )
    except CodeSpaceExhaustedError as exc:
        raise HTTPException(status_code=503, detail="CODE_SPACE_EXHAUSTED") from exc
    except sqlite3.OperationalError as exc:
        raise HTTPException(status_code=503, detail="Persistence unavailable") from exc

    if idempotency_key:
        idempotency_repository.record_result(conn, idempotency_key, api_key, link.code)

    return _to_response(link)


class BatchItem(BaseModel):
    target_url: str
    expires_at: str | None = None
    ttl_seconds: int | None = Field(default=None, gt=0)


class CreateBatchRequest(BaseModel):
    items: list[BatchItem]


class BatchItemResult(BaseModel):
    status: str  # "created" | "error"
    target_url: str
    code: str | None = None
    short_url: str | None = None
    expires_at: str | None = None
    error: str | None = None
    message: str | None = None


class BatchResponse(BaseModel):
    results: list[BatchItemResult]


@router.post("/api/v1/links/batch", response_model=BatchResponse)
def create_batch(
    body: CreateBatchRequest,
    api_key: str = Depends(enforce_rate_limit),
    conn: sqlite3.Connection = Depends(get_db),
) -> BatchResponse:
    """CL-01, FR-029: 1-25 items per call, per-item results, HTTP 200 even
    on partial failure. The whole batch is charged against the caller's
    rate limit up front (via enforce_rate_limit) — a 429 here creates
    nothing, since this handler body never runs. No batch-level idempotency
    (documented limitation; contract 1.0.0 -> 1.1.0, additive)."""
    if not (1 <= len(body.items) <= 25):
        raise HTTPException(status_code=400, detail="items must contain between 1 and 25 entries")

    results: list[BatchItemResult] = []
    for item in body.items:
        try:
            validate_target_url(item.target_url)
        except (InvalidUrlError, SsrfBlockedError) as exc:
            results.append(BatchItemResult(
                status="error", target_url=item.target_url, error="INVALID_URL", message=str(exc)
            ))
            continue

        expires_at = _resolve_expires_at(
            CreateLinkRequest(target_url=item.target_url, expires_at=item.expires_at, ttl_seconds=item.ttl_seconds)
        )
        try:
            code = generate_unique_code(exists=lambda c: links_repository.code_exists(conn, c))
            link = links_repository.create_link(
                conn, code=code, target_url=item.target_url, created_by=api_key, expires_at=expires_at,
            )
        except CodeSpaceExhaustedError:
            results.append(BatchItemResult(
                status="error", target_url=item.target_url, error="CODE_SPACE_EXHAUSTED",
                message="Could not generate a unique code",
            ))
            continue

        results.append(BatchItemResult(
            status="created", target_url=link.target_url, code=link.code,
            short_url=f"https://short.local/{link.code}", expires_at=link.expires_at,
        ))

    return BatchResponse(results=results)


def _to_response(link: links_repository.ShortLink) -> LinkResponse:
    return LinkResponse(
        code=link.code,
        short_url=f"https://short.local/{link.code}",
        target_url=link.target_url,
        expires_at=link.expires_at,
    )
