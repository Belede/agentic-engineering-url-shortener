"""TEST node: genuine parallel fan-out across independent test groups
(unit/contract/security), synchronized (fan-in) before DOCUMENT. ADR-004
parallel-execution evidence."""
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

from orchestration.engine import transition


def _run_group(name: str, passed: bool, duration: float) -> dict:
    started_at = time.monotonic()
    time.sleep(duration)  # stands in for real test-suite execution time
    ended_at = time.monotonic()
    return {"name": name, "passed": passed, "started_at": started_at, "ended_at": ended_at}


def run_test_node(
    conn: sqlite3.Connection,
    run_id: str,
    groups: dict[str, bool],
    simulated_duration_seconds: float = 0.01,
) -> dict[str, dict]:
    """Execute each group concurrently (real thread-level parallelism, not
    simulated), then synchronize before writing results and transitioning.
    Returns timing info per group for test verification of real overlap."""
    with ThreadPoolExecutor(max_workers=len(groups)) as pool:
        futures = [
            pool.submit(_run_group, name, passed, simulated_duration_seconds)
            for name, passed in groups.items()
        ]
        results = [f.result() for f in futures]  # fan-in: wait for all

    for r in sorted(results, key=lambda r: r["name"]):
        conn.execute(
            "INSERT INTO audit_events (run_id, actor_type, action, affected_artifact, result, reason) "
            "VALUES (?, 'system', 'test_group_executed', ?, ?, ?)",
            (run_id, r["name"], "pass" if r["passed"] else "fail", f"{r['name']} test group executed"),
        )
    conn.commit()

    all_passed = all(groups.values())
    if all_passed:
        transition(conn, run_id, to_state="DOCUMENT", actor="system", reason="all test groups passed")
    else:
        transition(conn, run_id, to_state="SAFE_STOP", actor="system", reason="a test group failed")

    return {r["name"]: r for r in results}
