"""T025: DOCUMENT node + fallback stub on doc-generator failure. ADR-006."""
from pathlib import Path

import pytest

from orchestration.engine import create_run, get_run, transition
from orchestration.nodes.document import run_document
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def run_at_document(tmp_path):
    conn = get_connection(str(tmp_path / "doc.db"))
    MigrationRunner(conn, MIGRATIONS_DIR).apply_all()
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version="1.0.0")
    for to_state, actor in [
        ("QUALITY_CHECK", "system"), ("DECOMPOSE", "system"), ("DESIGN", "system"),
        ("ARCH_APPROVAL", "system"), ("IMPLEMENT", "human"), ("TEST", "system"),
        ("DOCUMENT", "system"),
    ]:
        transition(conn, run_id, to_state=to_state, actor=actor, reason="x")
    yield conn, run_id
    conn.close()


def test_successful_doc_generation_transitions_to_release_approval(run_at_document):
    conn, run_id = run_at_document
    run_document(conn, run_id, generate_docs=lambda: "Updated docs/scenarios/greenfield.md")
    assert get_run(conn, run_id)["current_state"] == "RELEASE_APPROVAL"
    row = conn.execute(
        "SELECT content FROM decisions WHERE run_id = ? ORDER BY id DESC LIMIT 1", (run_id,)
    ).fetchone()
    assert "fallback" not in row["content"]


def test_doc_generator_failure_falls_back_without_blocking_the_run(run_at_document):
    """ADR-006: a doc-tooling outage must not block the whole run — it
    degrades to a labeled fallback stub and still proceeds."""
    conn, run_id = run_at_document

    def failing_generator():
        raise RuntimeError("doc-generator outage")

    run_document(conn, run_id, generate_docs=failing_generator)
    assert get_run(conn, run_id)["current_state"] == "RELEASE_APPROVAL"
    row = conn.execute(
        "SELECT content FROM decisions WHERE run_id = ? ORDER BY id DESC LIMIT 1", (run_id,)
    ).fetchone()
    assert "[fallback: doc-generator unavailable]" in row["content"]
