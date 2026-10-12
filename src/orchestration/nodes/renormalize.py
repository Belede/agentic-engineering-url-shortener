"""RENORMALIZE node: dynamic replanning after a human clarification answer.
FR-018, ADR-007. Computes a real before/after task diff (scoped regeneration)
rather than discarding and restarting — preserves decision lineage for
unaffected work."""
import json
import sqlite3

from orchestration.engine import transition


def diff_tasks(prior_tasks: list[str], new_tasks: list[str]) -> dict[str, list[str]]:
    prior_set, new_set = set(prior_tasks), set(new_tasks)
    return {
        "added": [t for t in new_tasks if t not in prior_set],
        "removed": [t for t in prior_tasks if t not in new_set],
        "unchanged": [t for t in new_tasks if t in prior_set],
    }


def run_renormalize(
    conn: sqlite3.Connection,
    run_id: str,
    new_requirement_text: str,
    prior_tasks: list[str],
    new_tasks: list[str],
) -> dict[str, list[str]]:
    diff = diff_tasks(prior_tasks, new_tasks)

    conn.execute(
        "INSERT INTO decisions (run_id, decision_type, content) VALUES (?, 'replan', ?)",
        (run_id, json.dumps({"requirement": new_requirement_text, **diff})),
    )
    conn.execute(
        "INSERT INTO audit_events (run_id, actor_type, action, affected_artifact, result, reason) "
        "VALUES (?, 'system', 'replanning', ?, 'success', ?)",
        (run_id, f"workflow_runs:{run_id}",
         f"added={len(diff['added'])} removed={len(diff['removed'])} unchanged={len(diff['unchanged'])}"),
    )
    conn.commit()

    transition(conn, run_id, to_state="DECOMPOSE", actor="system", reason="requirement re-normalized")
    return diff
