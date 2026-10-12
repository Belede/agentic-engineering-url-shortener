"""T035: policy evaluation engine + policy-pack v1.0.0. FR-027, constitution Principle VI."""
from pathlib import Path

import pytest

from orchestration.engine import create_run
from policy.engine import POLICY_PACK_VERSION, evaluate_policies, has_mandatory_failure
from shortener.persistence.db import get_connection
from shortener.persistence.migrations_runner import MigrationRunner

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "shortener" / "migrations"


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "policy.db"))
    MigrationRunner(c, MIGRATIONS_DIR).apply_all()
    yield c
    c.close()


def test_clean_run_passes_all_mandatory_policies(conn):
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version=POLICY_PACK_VERSION)
    results = evaluate_policies(conn, run_id, context={})
    assert has_mandatory_failure(results) is False
    assert all(r["outcome"] in ("PASS", "NOT-APPLICABLE") for r in results)


def test_every_evaluation_records_the_policy_version_evaluated(conn):
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version=POLICY_PACK_VERSION)
    evaluate_policies(conn, run_id, context={})
    rows = conn.execute(
        "SELECT policy_version FROM policy_evaluations WHERE run_id = ?", (run_id,)
    ).fetchall()
    assert len(rows) > 0
    assert all(r["policy_version"] == POLICY_PACK_VERSION for r in rows)


def test_ssrf_violation_fails_mandatory_security_policy(conn):
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version=POLICY_PACK_VERSION)
    results = evaluate_policies(conn, run_id, context={"ssrf_or_scheme_violation": True})
    assert has_mandatory_failure(results) is True
    sec = next(r for r in results if r["policy_id"] == "SEC-001")
    assert sec["outcome"] == "FAIL"


def test_unapproved_dependency_fails_mandatory_dependency_policy(conn):
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version=POLICY_PACK_VERSION)
    results = evaluate_policies(conn, run_id, context={"new_dependency_introduced": True})
    assert has_mandatory_failure(results) is True


def test_outcome_is_always_one_of_the_four_defined_values(conn):
    run_id = create_run(conn, requirement_input="x", scenario_type="greenfield", policy_pack_version=POLICY_PACK_VERSION)
    results = evaluate_policies(conn, run_id, context={"ssrf_or_scheme_violation": True})
    assert all(r["outcome"] in ("PASS", "FAIL", "EXCEPTION-REQUESTED", "NOT-APPLICABLE") for r in results)
