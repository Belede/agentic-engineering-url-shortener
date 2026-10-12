"""T043 (fault-injection variant 3/6): late ambiguity — discovered AFTER
initial design/approval, not just at intake. spec.md Scenario A promises:
'If material ambiguity emerges later, suspend only the affected path,
invoke governed clarification and impact analysis, and resume from the
correct state after explicit approval.'

This is a genuinely different path through the graph than the early-ambiguity
case (QUALITY_CHECK -> CLARIFY): here a requirement that INITIALLY passed all
6 quality checks and got as far as IMPLEMENT reveals a material ambiguity
during implementation (e.g. an edge case the design didn't anticipate).
"""
from pathlib import Path

import pytest

from orchestration.engine import create_run, get_run, transition
from orchestration.nodes.decompose import run_decompose
from orchestration.nodes.design import run_design
from orchestration.nodes.renormalize import run_renormalize
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def run_at_implement(tmp_path):
    conn = get_connection(str(tmp_path / "late_ambiguity.db"))
    MigrationRunner(conn, MIGRATIONS_DIR).apply_all()
    run_id = create_run(
        conn, requirement_input="Add a well-defined feature that later reveals an edge case",
        scenario_type="fault_injection", policy_pack_version="1.0.0",
    )
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="all 6 checks passed initially")
    transition(conn, run_id, to_state="DECOMPOSE", actor="system", reason="checks passed")
    run_decompose(conn, run_id, summary="initial task breakdown")
    run_design(conn, run_id, summary="initial design", security_sensitive=False)
    conn.execute(
        "INSERT INTO approval_records (run_id, gate, decision, decided_by, rationale) "
        "VALUES (?, 'ARCH_APPROVAL', 'approved', 'belede', 'looked complete at the time')",
        (run_id,),
    )
    conn.commit()
    transition(conn, run_id, to_state="IMPLEMENT", actor="human", reason="approved")
    yield conn, run_id
    conn.close()


def test_late_ambiguity_suspends_the_in_progress_implementation(run_at_implement):
    conn, run_id = run_at_implement
    assert get_run(conn, run_id)["current_state"] == "IMPLEMENT"

    # A material ambiguity is discovered mid-implementation — the design
    # did not specify behavior for a real edge case encountered while coding.
    conn.execute(
        "INSERT INTO decisions (run_id, decision_type, content) VALUES (?, 'assumption', ?)",
        (run_id, ("Design did not specify behavior for concurrent updates to the same "
                  "resource discovered during implementation — suspending for clarification")),
    )
    conn.commit()
    transition(conn, run_id, to_state="CLARIFY", actor="system", reason="late ambiguity discovered during implementation")

    assert get_run(conn, run_id)["current_state"] == "CLARIFY"


def test_late_ambiguity_resumes_only_the_affected_path_after_approval(run_at_implement):
    """Resume reuses the same governed RENORMALIZE machinery as early
    ambiguity — the mechanism is the same regardless of WHEN the ambiguity
    surfaces, satisfying spec.md's 'resume from the correct state after
    explicit approval' without needing a second, parallel implementation."""
    conn, run_id = run_at_implement
    transition(conn, run_id, to_state="CLARIFY", actor="system", reason="late ambiguity discovered")

    # Real clarification decision for this fault-injection variant.
    conn.execute(
        "INSERT INTO approval_records (run_id, gate, decision, decided_by, rationale) "
        "VALUES (?, 'CLARIFY', 'approved', 'belede', 'Use last-write-wins for this edge case')",
        (run_id,),
    )
    conn.commit()
    transition(conn, run_id, to_state="RENORMALIZE", actor="human", reason="clarified: last-write-wins")

    diff = run_renormalize(
        conn, run_id,
        new_requirement_text="...with last-write-wins for concurrent updates",
        prior_tasks=["initial task breakdown"],
        new_tasks=["initial task breakdown", "handle concurrent-update edge case (last-write-wins)"],
    )
    assert get_run(conn, run_id)["current_state"] == "DECOMPOSE"
    assert diff["added"] == ["handle concurrent-update edge case (last-write-wins)"]
    assert diff["unchanged"] == ["initial task breakdown"]  # the original, still-valid work is preserved
