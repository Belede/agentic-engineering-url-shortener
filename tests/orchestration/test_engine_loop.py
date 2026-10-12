"""T016: engine loop — dispatch, persist transition + audit event. ADR-004, ADR-008, FR-011, FR-025."""
import pytest

from orchestration.engine import InvalidTransitionError, create_run, get_run, transition
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = __import__("pathlib").Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "engine.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


def test_create_run_starts_at_ingest(conn):
    run_id = create_run(conn, requirement_input="add X", scenario_type="greenfield", policy_pack_version="1.0.0")
    run = get_run(conn, run_id)
    assert run["current_state"] == "INGEST"
    assert run["scenario_type"] == "greenfield"
    assert run["policy_pack_version"] == "1.0.0"


def test_create_run_persists_across_a_new_connection_read():
    """FR-011: workflow state MUST persist — not held only in process memory."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        db_path = f"{d}/persist.db"
        c1 = get_connection(db_path)
        MigrationRunner(c1, MIGRATIONS_DIR).apply_all()
        run_id = create_run(c1, requirement_input="add X", scenario_type="greenfield", policy_pack_version="1.0.0")
        c1.close()

        c2 = get_connection(db_path)  # simulates a fresh process reconnecting
        run = get_run(c2, run_id)
        c2.close()
        assert run["current_state"] == "INGEST"


def test_valid_transition_updates_current_state(conn):
    run_id = create_run(conn, requirement_input="add X", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalized")
    run = get_run(conn, run_id)
    assert run["current_state"] == "QUALITY_CHECK"


def test_invalid_transition_raises_and_does_not_change_state(conn):
    run_id = create_run(conn, requirement_input="add X", scenario_type="greenfield", policy_pack_version="1.0.0")
    with pytest.raises(InvalidTransitionError):
        transition(conn, run_id, to_state="DONE", actor="system", reason="skip ahead")
    run = get_run(conn, run_id)
    assert run["current_state"] == "INGEST"  # unchanged


def test_transition_records_state_transition_row(conn):
    run_id = create_run(conn, requirement_input="add X", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalized")
    rows = conn.execute(
        "SELECT from_state, to_state, actor, reason FROM state_transitions WHERE run_id = ? ORDER BY id",
        (run_id,),
    ).fetchall()
    # initial INGEST transition + the QUALITY_CHECK transition
    assert len(rows) == 2
    assert rows[1]["from_state"] == "INGEST"
    assert rows[1]["to_state"] == "QUALITY_CHECK"
    assert rows[1]["actor"] == "system"


def test_transition_records_audit_event(conn):
    run_id = create_run(conn, requirement_input="add X", scenario_type="greenfield", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalized")
    rows = conn.execute(
        "SELECT actor_type, action, affected_artifact, result FROM audit_events WHERE run_id = ? ORDER BY id",
        (run_id,),
    ).fetchall()
    assert len(rows) == 2  # create_run's initial transition + this one
    assert rows[1]["actor_type"] == "system"
    assert rows[1]["action"] == "state_transition"


def test_human_actor_transition_out_of_human_gate_succeeds(conn):
    run_id = create_run(conn, requirement_input="add X", scenario_type="ambiguous", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalized")
    transition(conn, run_id, to_state="CLARIFY", actor="system", reason="ambiguity detected")
    transition(conn, run_id, to_state="RENORMALIZE", actor="human", reason="human answered clarification")
    run = get_run(conn, run_id)
    assert run["current_state"] == "RENORMALIZE"


def test_system_actor_transition_out_of_human_gate_rejected(conn):
    """Runtime enforcement of ADR-005, mirroring the static graph test."""
    run_id = create_run(conn, requirement_input="add X", scenario_type="ambiguous", policy_pack_version="1.0.0")
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalized")
    transition(conn, run_id, to_state="CLARIFY", actor="system", reason="ambiguity detected")
    with pytest.raises(InvalidTransitionError):
        transition(conn, run_id, to_state="RENORMALIZE", actor="system", reason="auto-advance attempt")
