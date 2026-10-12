"""T042: Ambiguous scenario — resumption after the REAL human clarification
answer (not fabricated). CL-03 resolution.

Real decision, given by the human candidate via chat on 2026-10-12:
"New links only" — new links get a default expiry unless the caller opts
out; existing (already-shared) links are never retroactively affected.
This resolves the original contradiction by scoping expiry to creation
time rather than applying it globally.
"""
from pathlib import Path

import pytest

from orchestration.engine import create_run, get_run, transition
from orchestration.nodes.decompose import run_decompose
from orchestration.nodes.design import run_design
from orchestration.nodes.document import run_document
from orchestration.nodes.implement import run_implement
from orchestration.nodes.renormalize import run_renormalize
from orchestration.nodes.test_node import run_test_node
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"

AMBIGUOUS_REQUIREMENT = (
    "Links should expire automatically after a while, but links that have "
    "already been shared must never break."
)
REAL_HUMAN_ANSWER = (
    "New links only: new links get a default 90-day expiry unless the caller "
    "sets expires_at/ttl_seconds or passes no_expiry=true. Existing links are "
    "never retroactively affected."
)


@pytest.fixture
def run_at_clarify(tmp_path):
    conn = get_connection(str(tmp_path / "resume.db"))
    MigrationRunner(conn, MIGRATIONS_DIR).apply_all()
    run_id = create_run(
        conn, requirement_input=AMBIGUOUS_REQUIREMENT,
        scenario_type="ambiguous", policy_pack_version="1.0.0",
    )
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalizing")
    transition(conn, run_id, to_state="CLARIFY", actor="system", reason="ambiguity detected")
    yield conn, run_id
    conn.close()


def test_clarify_endpoint_records_the_real_answer_and_resumes(run_at_clarify):
    from fastapi.testclient import TestClient

    from shortener.api.app import create_app

    conn, run_id = run_at_clarify
    db_path = conn.execute("PRAGMA database_list").fetchone()["file"]
    conn.close()  # release before the API opens its own connection to the same file

    app = create_app(db_path=db_path)
    client = TestClient(app)

    resp = client.post(
        f"/api/v1/workflows/{run_id}/clarify",
        json={
            "answer": REAL_HUMAN_ANSWER,
            "decided_by": "belede",
            "rationale": "Resolves the contradiction by scoping expiry to creation time, "
                         "not applying it retroactively to already-shared links.",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["current_state"] == "RENORMALIZE"


def test_renormalize_produces_a_real_task_diff_for_the_resolved_requirement(run_at_clarify):
    conn, run_id = run_at_clarify
    transition(conn, run_id, to_state="RENORMALIZE", actor="human", reason="human answered: new links only")

    diff = run_renormalize(
        conn, run_id,
        new_requirement_text=REAL_HUMAN_ANSWER,
        prior_tasks=["task: implement expiry (blocked — contradictory)"],
        new_tasks=[
            "task: add SHORTENER_DEFAULT_TTL_DAYS config (default 90, max 365)",
            "task: apply default only at link-creation time for new links",
            "task: add no_expiry=true opt-out to CreateLinkRequest",
        ],
    )
    assert get_run(conn, run_id)["current_state"] == "DECOMPOSE"
    assert len(diff["added"]) == 3
    assert diff["removed"] == ["task: implement expiry (blocked — contradictory)"]


def test_design_for_the_resolved_requirement_is_flagged_security_sensitive(run_at_clarify):
    """config.py is a security-sensitive file per ADR scope — this design
    must route through SECURITY_APPROVAL, not just ARCH_APPROVAL."""
    conn, run_id = run_at_clarify
    transition(conn, run_id, to_state="RENORMALIZE", actor="human", reason="human answered")
    run_renormalize(
        conn, run_id, new_requirement_text=REAL_HUMAN_ANSWER,
        prior_tasks=[], new_tasks=["task: add SHORTENER_DEFAULT_TTL_DAYS config"],
    )
    run_decompose(conn, run_id, summary="Add default-TTL config and new-links-only application")

    run_design(
        conn, run_id,
        summary="Add SHORTENER_DEFAULT_TTL_DAYS (default 90, validated <= 365) to "
                "src/shortener/config.py; applied only at creation time for new links "
                "with no expires_at/ttl_seconds and no_expiry != true. No migration "
                "(reuses existing expires_at column). Contract 1.2.0 -> 1.3.0.",
        security_sensitive=True,
    )
    assert get_run(conn, run_id)["current_state"] == "ARCH_APPROVAL"
    row = conn.execute(
        "SELECT security_sensitive FROM workflow_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row["security_sensitive"] == 1


def test_full_run_reaches_release_approval_after_real_human_approvals(run_at_clarify):
    """The complete, real governed sequence for this scenario: human
    clarification -> replan -> design -> REAL ARCH_APPROVAL -> REAL
    SECURITY_APPROVAL (both given by Belede Rahul via chat, 2026-10-12) ->
    implement -> test -> document -> parked at RELEASE_APPROVAL (deliberately
    not auto-approved here — release readiness is a separate, later gate
    covering all three scenarios together)."""
    conn, run_id = run_at_clarify
    transition(conn, run_id, to_state="RENORMALIZE", actor="human", reason="human answered: new links only")
    run_renormalize(
        conn, run_id, new_requirement_text=REAL_HUMAN_ANSWER,
        prior_tasks=[], new_tasks=["task: add SHORTENER_DEFAULT_TTL_DAYS config"],
    )
    run_decompose(conn, run_id, summary="Add default-TTL config and new-links-only application")
    run_design(
        conn, run_id,
        summary="SHORTENER_DEFAULT_TTL_DAYS (default 90, max 365); new-links-only; "
                "no_expiry=true opt-out; contract 1.2.0 -> 1.3.0",
        security_sensitive=True,
    )

    conn.execute(
        "INSERT INTO approval_records (run_id, gate, decision, decided_by, rationale) "
        "VALUES (?, 'ARCH_APPROVAL', 'approved', 'belede', ?)",
        (run_id, "Approved both ARCH and SECURITY aspects together, 2026-10-12"),
    )
    conn.commit()
    transition(conn, run_id, to_state="SECURITY_APPROVAL", actor="human", reason="approved, config.py touched")

    conn.execute(
        "INSERT INTO approval_records (run_id, gate, decision, decided_by, rationale) "
        "VALUES (?, 'SECURITY_APPROVAL', 'approved', 'belede', ?)",
        (run_id, "Validated default_ttl_days bound (<=365), no secret exposure"),
    )
    conn.commit()
    transition(conn, run_id, to_state="IMPLEMENT", actor="human", reason="approved")

    run_implement(conn, run_id, summary="Added SHORTENER_DEFAULT_TTL_DAYS to config.py; "
                                         "new-links-only default TTL + no_expiry opt-out in links.py")
    run_test_node(conn, run_id, groups={"unit": True, "contract": True, "security": True})
    assert get_run(conn, run_id)["current_state"] == "DOCUMENT"

    run_document(conn, run_id, generate_docs=lambda: "Updated docs/scenarios/ambiguous.md and contracts/openapi.yaml to 1.3.0")
    assert get_run(conn, run_id)["current_state"] == "RELEASE_APPROVAL"

    # Deliberately NOT advanced further — release readiness is covered by
    # the final, combined release-readiness decision (Phase 5), not
    # fabricated here.
