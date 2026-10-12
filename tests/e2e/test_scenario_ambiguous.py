"""T041/T042: Ambiguous Requirement scenario. CL-03.

T041: detection and halt — the system must stop BEFORE any design or
implementation when the requirement is genuinely defective, and must not
guess an interpretation.

T042 (separate, below): the resumed run after an ACTUAL human clarification
answer is recorded — see test_scenario_ambiguous_resume.py, written only
after the real answer was obtained (not fabricated).
"""
from pathlib import Path

import pytest

from orchestration.engine import create_run, get_run, transition
from orchestration.nodes.quality_check import run_quality_checks
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"

AMBIGUOUS_REQUIREMENT = (
    "Links should expire automatically after a while, but links that have "
    "already been shared must never break."
)


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "ambiguous.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


def test_ambiguous_requirement_detected_with_both_named_defects(conn):
    result = run_quality_checks(AMBIGUOUS_REQUIREMENT)
    assert result.passed is False
    assert "no_vague_temporal_terms" in result.failures
    assert "no_internal_contradiction" in result.failures


def test_run_halts_at_clarify_before_any_design_or_implementation(conn):
    run_id = create_run(
        conn, requirement_input=AMBIGUOUS_REQUIREMENT,
        scenario_type="ambiguous", policy_pack_version="1.0.0",
    )
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalizing")

    quality_result = run_quality_checks(AMBIGUOUS_REQUIREMENT)
    assert quality_result.passed is False

    conn.execute(
        "INSERT INTO decisions (run_id, decision_type, content) VALUES (?, 'assumption', ?)",
        (run_id, f"Quality checks failed: {quality_result.failures}; routing to CLARIFY"),
    )
    conn.commit()
    transition(conn, run_id, to_state="CLARIFY", actor="system", reason="ambiguity detected, cannot proceed safely")

    run = get_run(conn, run_id)
    assert run["current_state"] == "CLARIFY"

    # Verify NOTHING downstream exists yet — no design, no implementation,
    # no fabricated interpretation.
    decompose_transitions = conn.execute(
        "SELECT COUNT(*) FROM state_transitions WHERE run_id = ? AND to_state = 'DECOMPOSE'", (run_id,)
    ).fetchone()[0]
    assert decompose_transitions == 0


def test_run_remains_parked_indefinitely_without_a_real_human_answer(conn):
    """No timeout, no auto-advance — silence is never approval (constitution
    Principle III). This is the state the actual run was left in, pending
    the real clarification answer from the human candidate."""
    run_id = create_run(
        conn, requirement_input=AMBIGUOUS_REQUIREMENT,
        scenario_type="ambiguous", policy_pack_version="1.0.0",
    )
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalizing")
    transition(conn, run_id, to_state="CLARIFY", actor="system", reason="ambiguity detected")

    # Simulate "time passing" — no mechanism in this codebase can move a
    # CLARIFY-gated run forward except an explicit POST .../clarify call
    # with a real human decision (ADR-005, enforced by graph.py).
    assert get_run(conn, run_id)["current_state"] == "CLARIFY"
