"""Orchestration HTTP API: workflow creation, inspection, and human-gate
decisions (clarify/approve/reject/resume). FR-012, FR-013, FR-017, ADR-005.

This module accumulates the human-gate endpoints as they're implemented
(clarify here in T018; arch/security/release approval in T021/T022/T026;
inspection in T027; resume in T031) rather than one file per endpoint,
since they share the same "load the run, validate current gate, record
decision, transition" shape.
"""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from orchestration.engine import InvalidTransitionError, get_run, transition
from shortener.api.deps import get_db

router = APIRouter()


class ClarifyRequest(BaseModel):
    answer: str
    decided_by: str
    rationale: str


class ApproveRequest(BaseModel):
    gate: str  # "ARCH_APPROVAL" | "SECURITY_APPROVAL" | "RELEASE_APPROVAL"
    decision: str  # "approved" | "rejected"
    decided_by: str
    rationale: str


# For each (gate, decision) pair that is NOT RELEASE_APPROVAL (handled
# separately in T026 — it has a three-way READY/LIMITATIONS/NOT_READY
# outcome rather than a plain approve/reject), the target state when
# approved may depend on run state (security_sensitive) — handled in code
# below rather than this static table for ARCH_APPROVAL's branch.
REJECT_TARGET = "SAFE_STOP"


class WorkflowStateResponse(BaseModel):
    run_id: str
    current_state: str
    scenario_type: str


def _require_run(conn: sqlite3.Connection, run_id: str) -> dict:
    try:
        return get_run(conn, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown run") from exc


@router.post("/api/v1/workflows/{run_id}/clarify", response_model=WorkflowStateResponse)
def clarify(
    run_id: str,
    body: ClarifyRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> WorkflowStateResponse:
    run = _require_run(conn, run_id)
    if run["current_state"] != "CLARIFY":
        raise HTTPException(
            status_code=409,
            detail=f"Run is at {run['current_state']!r}, not CLARIFY",
        )

    conn.execute(
        "INSERT INTO decisions (run_id, decision_type, content, source_reference) "
        "VALUES (?, 'clarification', ?, ?)",
        (run_id, body.answer, body.rationale),
    )
    conn.execute(
        "INSERT INTO approval_records (run_id, gate, decision, decided_by, rationale) "
        "VALUES (?, 'CLARIFY', 'approved', ?, ?)",
        (run_id, body.decided_by, body.rationale),
    )
    conn.commit()

    try:
        transition(conn, run_id, to_state="RENORMALIZE", actor="human", reason=body.rationale)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    run = get_run(conn, run_id)
    return WorkflowStateResponse(
        run_id=run_id, current_state=run["current_state"], scenario_type=run["scenario_type"]
    )


@router.post("/api/v1/workflows/{run_id}/approve", response_model=WorkflowStateResponse)
def approve(
    run_id: str,
    body: ApproveRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> WorkflowStateResponse:
    """Handles ARCH_APPROVAL and SECURITY_APPROVAL (T021/T022). RELEASE_APPROVAL
    has its own endpoint (T026) since it carries a three-way outcome, not a
    plain approve/reject."""
    run = _require_run(conn, run_id)
    if run["current_state"] != body.gate:
        raise HTTPException(
            status_code=409,
            detail=f"Run is at {run['current_state']!r}, not {body.gate!r}",
        )
    if body.gate not in ("ARCH_APPROVAL", "SECURITY_APPROVAL"):
        raise HTTPException(status_code=400, detail=f"Unsupported gate for this endpoint: {body.gate!r}")

    conn.execute(
        "INSERT INTO approval_records (run_id, gate, decision, decided_by, rationale) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_id, body.gate, body.decision, body.decided_by, body.rationale),
    )
    conn.commit()

    if body.decision == "rejected":
        target = REJECT_TARGET
    elif body.gate == "ARCH_APPROVAL":
        target = "SECURITY_APPROVAL" if run["security_sensitive"] else "IMPLEMENT"
    else:  # SECURITY_APPROVAL approved
        target = "IMPLEMENT"

    try:
        transition(conn, run_id, to_state=target, actor="human", reason=body.rationale)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    run = get_run(conn, run_id)
    return WorkflowStateResponse(
        run_id=run_id, current_state=run["current_state"], scenario_type=run["scenario_type"]
    )
