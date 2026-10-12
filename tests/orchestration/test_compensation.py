"""T030: compensation mechanism — always human-approved. FR-023, ADR-006."""
from pathlib import Path

import pytest

from orchestration.reliability.compensation import (
    CompensatingAction,
    CompensationNotApprovedError,
    compensate,
)
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "compensation.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


def test_compensate_requires_an_approved_by_identity(conn):
    from orchestration.engine import create_run
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    action = CompensatingAction(
        change_description="migration applied to sandbox",
        compensating_control="documented as known deviation, verified safe",
        approved_by="",  # empty — not approved
    )
    with pytest.raises(CompensationNotApprovedError):
        compensate(conn, run_id, action)


def test_compensate_with_approval_records_audit_event(conn):
    from orchestration.engine import create_run
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    action = CompensatingAction(
        change_description="migration applied to sandbox",
        compensating_control="documented as known deviation, verified safe",
        approved_by="belede",
    )
    compensate(conn, run_id, action)

    row = conn.execute(
        "SELECT action, result, reason FROM audit_events WHERE run_id = ? AND action = 'compensation'",
        (run_id,),
    ).fetchone()
    assert row is not None
    assert row["result"] == "success"
    assert "belede" in row["reason"]
