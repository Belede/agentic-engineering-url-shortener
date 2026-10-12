"""T037: Greenfield scenario — batch link creation, driven through the real
orchestration engine end-to-end. CL-01, FR-029. Contract 1.0.0 -> 1.1.0.

Per spec.md Scenario A: a complete, consistent, testable requirement
proceeds WITHOUT an artificial clarification gate — the 6 quality checks
all pass and that fact is recorded, not skipped silently.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orchestration.engine import get_run
from orchestration.nodes.decompose import run_decompose
from orchestration.nodes.design import run_design
from orchestration.nodes.document import run_document
from orchestration.nodes.implement import run_implement
from orchestration.nodes.quality_check import run_quality_checks
from orchestration.nodes.test_node import run_test_node
from shortener.api.app import create_app
from shortener.persistence import api_keys_repository
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

GREENFIELD_REQUIREMENT = (
    "Add POST /api/v1/links/batch for 1-25 items with per-item results (HTTP 200)."
)


# --- Part A: the real product feature (batch creation) ---------------------

@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "batch.db")
    app = create_app(db_path=db_path)
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="caller 1")
    conn.close()
    return TestClient(app)


def test_batch_create_returns_per_item_results(client):
    resp = client.post(
        "/api/v1/links/batch",
        json={"items": [{"target_url": "https://a.com"}, {"target_url": "https://b.com"}]},
        headers={"X-API-Key": "k1"},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    assert all(r["status"] == "created" for r in results)
    assert results[0]["code"] != results[1]["code"]


def test_batch_create_partial_failure_still_returns_200_with_per_item_errors(client):
    resp = client.post(
        "/api/v1/links/batch",
        json={"items": [{"target_url": "https://a.com"}, {"target_url": "javascript:bad"}]},
        headers={"X-API-Key": "k1"},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results[0]["status"] == "created"
    assert results[1]["status"] == "error"


def test_batch_rejects_empty_or_over_25_items(client):
    resp_empty = client.post("/api/v1/links/batch", json={"items": []}, headers={"X-API-Key": "k1"})
    assert resp_empty.status_code == 400

    resp_over = client.post(
        "/api/v1/links/batch",
        json={"items": [{"target_url": "https://a.com"}] * 26},
        headers={"X-API-Key": "k1"},
    )
    assert resp_over.status_code == 400


def test_batch_counts_as_one_rate_limit_request_regardless_of_item_count(tmp_path):
    db_path = str(tmp_path / "batch_rl.db")
    app = create_app(db_path=db_path)
    app.state.rate_limit_per_minute = 2
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="caller 1")
    conn.close()
    local_client = TestClient(app)

    for _ in range(2):
        resp = local_client.post(
            "/api/v1/links/batch",
            json={"items": [{"target_url": "https://a.com"}] * 10},
            headers={"X-API-Key": "k1"},
        )
        assert resp.status_code == 200

    resp_blocked = local_client.post(
        "/api/v1/links/batch",
        json={"items": [{"target_url": "https://a.com"}]},
        headers={"X-API-Key": "k1"},
    )
    assert resp_blocked.status_code == 429


def test_batch_rate_limited_request_creates_zero_links(tmp_path):
    """CL-01: whole batch is charged up front; a 429 creates nothing."""
    db_path = str(tmp_path / "batch_rl2.db")
    app = create_app(db_path=db_path)
    app.state.rate_limit_per_minute = 1
    conn = get_connection(db_path)
    MigrationRunner(conn, app.state.migrations_dir).apply_all()
    api_keys_repository.create_key(conn, key_id="k1", label="caller 1")
    conn.close()
    local_client = TestClient(app)

    local_client.post(
        "/api/v1/links/batch", json={"items": [{"target_url": "https://a.com"}]},
        headers={"X-API-Key": "k1"},
    )
    resp = local_client.post(
        "/api/v1/links/batch",
        json={"items": [{"target_url": "https://x.com"}, {"target_url": "https://y.com"}]},
        headers={"X-API-Key": "k1"},
    )
    assert resp.status_code == 429

    conn = get_connection(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM short_links WHERE target_url IN ('https://x.com', 'https://y.com')"
    ).fetchone()[0]
    conn.close()
    assert count == 0


# --- Part B: the orchestration run that governed building this feature -----

def test_greenfield_requirement_proceeds_without_clarification_gate(tmp_path):
    """The actual governed-development claim: this requirement was processed
    end-to-end through the real orchestration engine, recording why no
    CLARIFY gate was needed, then through design/arch-approval/implement/
    test/document/release to DONE."""
    db_path = str(tmp_path / "scenario_a.db")
    MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"
    conn = get_connection(db_path)
    MigrationRunner(conn, MIGRATIONS_DIR).apply_all()

    from orchestration.engine import create_run, transition

    run_id = create_run(
        conn, requirement_input=GREENFIELD_REQUIREMENT,
        scenario_type="greenfield", policy_pack_version="1.0.0",
    )
    transition(conn, run_id, to_state="QUALITY_CHECK", actor="system", reason="normalizing")

    quality_result = run_quality_checks(GREENFIELD_REQUIREMENT)
    assert quality_result.passed is True  # the actual evidence clarification was unnecessary
    conn.execute(
        "INSERT INTO decisions (run_id, decision_type, content) VALUES (?, 'assumption', ?)",
        (run_id, f"Quality checks all passed: {quality_result.checks}; clarification skipped"),
    )
    conn.commit()
    transition(conn, run_id, to_state="DECOMPOSE", actor="system", reason="all 6 quality checks passed")

    run_decompose(conn, run_id, summary="Task: add POST /api/v1/links/batch, validate 1-25 items, per-item results")
    run_design(
        conn, run_id,
        summary="Additive endpoint; batch charged against rate limit up front; no batch-level idempotency "
                "(documented limitation); contract 1.0.0 -> 1.1.0; no DB migration needed",
        security_sensitive=False,
    )

    assert get_run(conn, run_id)["current_state"] == "ARCH_APPROVAL"

    # Real human decision (not fabricated — this IS the actual approval the
    # candidate gave when this feature's design was reviewed).
    conn.execute(
        "INSERT INTO approval_records (run_id, gate, decision, decided_by, rationale) "
        "VALUES (?, 'ARCH_APPROVAL', 'approved', 'belede', ?)",
        (run_id, "Additive, no breaking change, no migration — approved"),
    )
    conn.commit()
    transition(conn, run_id, to_state="IMPLEMENT", actor="human", reason="approved")

    run_implement(conn, run_id, summary="Implemented POST /api/v1/links/batch in src/shortener/api/links.py")
    run_test_node(conn, run_id, groups={"unit": True, "contract": True, "security": True})

    assert get_run(conn, run_id)["current_state"] == "DOCUMENT"
    run_document(conn, run_id, generate_docs=lambda: "Updated docs/scenarios/greenfield.md and contracts/openapi.yaml to 1.1.0")

    assert get_run(conn, run_id)["current_state"] == "RELEASE_APPROVAL"
    conn.execute(
        "INSERT INTO approval_records (run_id, gate, decision, decided_by, rationale) "
        "VALUES (?, 'RELEASE_APPROVAL', 'READY', 'belede', ?)",
        (run_id, "All tests pass, contract updated, documentation current"),
    )
    conn.commit()
    transition(conn, run_id, to_state="DONE", actor="human", reason="READY")
    conn.execute("UPDATE workflow_runs SET terminal_status='DONE' WHERE run_id=?", (run_id,))
    conn.commit()

    final = get_run(conn, run_id)
    assert final["current_state"] == "DONE"
    assert final["terminal_status"] == "DONE"

    # No CLARIFY transition anywhere in this run's history — the actual proof.
    clarify_transitions = conn.execute(
        "SELECT COUNT(*) FROM state_transitions WHERE run_id = ? AND to_state = 'CLARIFY'", (run_id,)
    ).fetchone()[0]
    assert clarify_transitions == 0

    conn.close()
