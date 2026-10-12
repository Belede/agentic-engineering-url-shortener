"""Bounded retry with exponential backoff and explicit failure classification.
FR-022, NFR-002, ADR-006. Max 2 retries (3 total attempts by default),
backoff 1s -> 2s -> 4s, capped."""
import time
from collections.abc import Callable

BACKOFF_SCHEDULE = (1, 2, 4)


class TransientError(Exception):
    """A failure classified as transient (eligible for retry) — e.g. a DB
    connection/I/O error. Narrow and explicit by design (ADR-006): only
    code that raises this type is ever retried."""


class PermanentError(Exception):
    """A failure classified as permanent (not retried) — e.g. a domain
    validation failure or policy FAIL."""


class RetryExhaustedError(RuntimeError):
    """Raised when max_attempts consecutive TransientErrors occur. The
    caller is expected to route this to SAFE_STOP (FR-024)."""


def with_bounded_retry(
    fn: Callable[[], object],
    max_attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> object:
    last_exc: TransientError | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except TransientError as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                backoff = BACKOFF_SCHEDULE[min(attempt, len(BACKOFF_SCHEDULE) - 1)]
                sleep(backoff)
    raise RetryExhaustedError(
        f"Exhausted {max_attempts} attempts; last error: {last_exc}"
    ) from last_exc
