"""T028: bounded retry + transient/permanent classification. FR-022, NFR-002, ADR-006."""
import pytest

from orchestration.reliability.retry import (
    PermanentError,
    RetryExhaustedError,
    TransientError,
    with_bounded_retry,
)


def test_succeeds_on_first_attempt_without_retry():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        return "ok"

    result = with_bounded_retry(fn, max_attempts=3, sleep=lambda s: None)
    assert result == "ok"
    assert calls["n"] == 1


def test_retries_transient_failure_then_succeeds():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TransientError("db locked")
        return "ok"

    result = with_bounded_retry(fn, max_attempts=3, sleep=lambda s: None)
    assert result == "ok"
    assert calls["n"] == 3


def test_exhausts_after_max_attempts_and_raises_retry_exhausted():
    """FR-022, NFR-002: bounded — never unlimited retry."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise TransientError("db locked")

    with pytest.raises(RetryExhaustedError):
        with_bounded_retry(fn, max_attempts=2, sleep=lambda s: None)
    assert calls["n"] == 2  # exactly bounded, not more


def test_permanent_error_is_not_retried():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise PermanentError("invalid input")

    with pytest.raises(PermanentError):
        with_bounded_retry(fn, max_attempts=3, sleep=lambda s: None)
    assert calls["n"] == 1  # no retry attempted


def test_backoff_uses_exponential_schedule():
    sleeps = []

    def fn():
        raise TransientError("x")

    with pytest.raises(RetryExhaustedError):
        with_bounded_retry(fn, max_attempts=3, sleep=lambda s: sleeps.append(s))
    assert sleeps == [1, 2]  # backoff before attempts 2 and 3, not after the last
