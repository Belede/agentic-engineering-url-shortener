"""T029: rollback mechanism with an explicit, testable feasibility predicate.
FR-023, ADR-006, independent-review condition #2 (no implicit judgment call)."""
from pathlib import Path

import pytest

from orchestration.reliability.rollback import (
    Change,
    RollbackInfeasibleError,
    is_rollback_feasible,
    rollback,
)
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "rollback.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


def test_change_not_applied_externally_is_feasible():
    change = Change(description="uncommitted design doc", applied_externally=False)
    assert is_rollback_feasible(change) is True


def test_change_applied_externally_is_not_feasible():
    change = Change(description="migration already run against sandbox DB", applied_externally=True)
    assert is_rollback_feasible(change) is False


def test_rollback_succeeds_for_feasible_change_and_records_audit_event(conn):
    from orchestration.engine import create_run
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    change = Change(description="uncommitted design doc", applied_externally=False)

    rollback(conn, run_id, change)

    row = conn.execute(
        "SELECT action, affected_artifact, result FROM audit_events "
        "WHERE run_id = ? AND action = 'rollback'",
        (run_id,),
    ).fetchone()
    assert row is not None
    assert row["result"] == "success"


def test_rollback_raises_for_infeasible_change_rather_than_silently_pretending(conn):
    """The predicate is enforced, not merely documented — attempting rollback
    on an externally-applied change must fail loudly, routing the caller to
    compensation instead (ADR-006)."""
    from orchestration.engine import create_run
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    change = Change(description="migration already applied", applied_externally=True)

    with pytest.raises(RollbackInfeasibleError):
        rollback(conn, run_id, change)
