"""T036: policy-exception workflow — approval, rationale, expiry, compensating control.
constitution Principle VI."""
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from orchestration.engine import create_run
from policy.engine import evaluate_policies, has_mandatory_failure
from policy.exceptions import (
    ExceptionNotApprovedError,
    PolicyException,
    apply_exception,
    is_exception_valid,
)
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "exception.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


def test_exception_requires_approving_authority(conn):
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    exc = PolicyException(
        policy_id="DEP-001", reason="vetted manually", scope="this run only",
        approving_authority="", compensating_control="manual review done",
        expires_at=future,
    )
    with pytest.raises(ExceptionNotApprovedError):
        apply_exception(conn, exc)


def test_approved_exception_is_recorded_with_all_required_fields(conn):
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    exc = PolicyException(
        policy_id="DEP-001", reason="vetted manually", scope="this run only",
        approving_authority="belede", compensating_control="manual review done",
        expires_at=future,
    )
    exception_id = apply_exception(conn, exc)
    row = conn.execute(
        "SELECT policy_id, reason, scope, approving_authority, compensating_control, expires_at "
        "FROM policy_exceptions WHERE id = ?", (exception_id,),
    ).fetchone()
    assert row["policy_id"] == "DEP-001"
    assert row["approving_authority"] == "belede"


def test_exception_is_valid_before_expiry(conn):
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    exc = PolicyException(
        policy_id="DEP-001", reason="x", scope="x",
        approving_authority="belede", compensating_control="x", expires_at=future,
    )
    exception_id = apply_exception(conn, exc)
    assert is_exception_valid(conn, exception_id) is True


def test_expired_exception_is_not_valid(conn):
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    exc = PolicyException(
        policy_id="DEP-001", reason="x", scope="x",
        approving_authority="belede", compensating_control="x", expires_at=past,
    )
    exception_id = apply_exception(conn, exc)
    assert is_exception_valid(conn, exception_id) is False


def test_a_valid_exception_removes_the_mandatory_block(conn):
    """An EXCEPTION-REQUESTED outcome with a valid, approved exception does
    not block progression; an expired or missing exception still does."""
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    results = evaluate_policies(conn, run_id, context={"new_dependency_introduced": True})
    assert has_mandatory_failure(results) is True  # blocked before any exception

    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    exc = PolicyException(
        policy_id="DEP-001", reason="reviewed", scope="this run",
        approving_authority="belede", compensating_control="manual audit", expires_at=future,
    )
    exception_id = apply_exception(conn, exc)

    results_with_exception = evaluate_policies(
        conn, run_id, context={"new_dependency_introduced": True, "exception_id": exception_id}
    )
    dep_result = next(r for r in results_with_exception if r["policy_id"] == "DEP-001")
    assert dep_result["outcome"] == "EXCEPTION-REQUESTED"
    assert has_mandatory_failure(results_with_exception) is False
