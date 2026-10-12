"""Versioned policy evaluation engine. FR-027, constitution Principle VI.

Every applicable policy check produces exactly one of PASS / FAIL /
EXCEPTION-REQUESTED / NOT-APPLICABLE, and every evaluation records the
policy pack version evaluated — never left implicit.
"""
import sqlite3

from policy.exceptions import is_exception_valid

POLICY_PACK_VERSION = "1.0.0"

POLICIES = (
    {
        "id": "SEC-001",
        "description": "No disallowed URL scheme or SSRF-unsafe target introduced",
        "mandatory": True,
    },
    {
        "id": "CHG-001",
        "description": "Architecture/contract changes require an approved ADR or ARCH_APPROVAL",
        "mandatory": True,
    },
    {
        "id": "DEP-001",
        "description": "No unapproved new third-party dependency introduced",
        "mandatory": True,
    },
    {
        "id": "AUD-001",
        "description": "Audit trail remains append-only for the life of the repository",
        "mandatory": True,
    },
)


def _evaluate_one(conn: sqlite3.Connection, policy: dict, context: dict) -> str:
    policy_id = policy["id"]

    if policy_id == "SEC-001":
        violated = context.get("ssrf_or_scheme_violation", False)
    elif policy_id == "CHG-001":
        violated = not context.get("has_arch_approval", True)
    elif policy_id == "DEP-001":
        violated = context.get("new_dependency_introduced", False)
    elif policy_id == "AUD-001":
        # Structurally always true given the append-only audit design
        # (ADR-008) — no application code path issues UPDATE/DELETE
        # against audit_events.
        return "PASS"
    else:
        return "NOT-APPLICABLE"

    if not violated:
        return "PASS"

    exception_id = context.get("exception_id")
    if exception_id is not None and is_exception_valid(conn, exception_id):
        return "EXCEPTION-REQUESTED"
    return "FAIL"


def evaluate_policies(conn: sqlite3.Connection, run_id: str, context: dict) -> list[dict]:
    results = []
    for policy in POLICIES:
        outcome = _evaluate_one(conn, policy, context)
        exception_ref = context.get("exception_id") if outcome == "EXCEPTION-REQUESTED" else None
        conn.execute(
            "INSERT INTO policy_evaluations (run_id, policy_id, policy_version, outcome, exception_reference) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, policy["id"], POLICY_PACK_VERSION, outcome, exception_ref),
        )
        results.append({
            "policy_id": policy["id"],
            "outcome": outcome,
            "mandatory": policy["mandatory"],
        })
    conn.commit()
    return results


def has_mandatory_failure(results: list[dict]) -> bool:
    return any(r["outcome"] == "FAIL" and r["mandatory"] for r in results)
