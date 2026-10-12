# ADR-005: Human Approval Model

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

Constitution Principle III requires that mandatory approval gates are never silently skipped and that silence is never interpreted as approval. The orchestration engine must implement this as an actual technical control, not just a documentation promise.

## Decision Drivers

- Must be impossible for a run to auto-advance past a human-gate node
- Must be simple enough for a reviewer to exercise manually (API call or CLI) within the timebox
- Must record who approved, when, and why

## Options Considered

### Option 1: Human-gate nodes have no outbound "system" transition — only an explicit `POST /api/v1/workflows/{run_id}/approve` or `/reject` call can move the state

- Advantages: enforced at the state-machine level, not just by convention — a unit test can assert "no transition out of `ARCH_APPROVAL` exists in the graph definition except via an explicit approval/rejection action with a recorded actor"
- Disadvantages: requires the reviewer to know to call the approval endpoint (mitigated by the reviewer navigation guide)
- Risks: none material
- Implementation impact: low-medium
- Assessment implications: directly testable and directly demoable

### Option 2: Timeout-based auto-approval after N minutes

- Advantages: convenient for unattended demo runs
- Disadvantages: directly violates constitution Principle III ("lack of response must not be interpreted as approval") — explicitly prohibited
- Risks: fails a non-negotiable constitutional principle
- Implementation impact: n/a — rejected outright

### Option 3: Approval via editing a file/config flag manually

- Advantages: no API needed
- Disadvantages: no structured record of actor/timestamp/rationale; easy to fabricate or backdate; weak audit evidence
- Risks: undermines Evidence-Based Completion (Principle XI)
- Implementation impact: low but low-quality
- Assessment implications: weak evidence story

## Decision

Adopt **Option 1**: human-gate nodes have zero system-initiated outbound transitions; approval/rejection is an explicit, authenticated-by-caller API action recorded in `approval_records` with gate, run id, decision, decided-by, timestamp, and rationale.

## Rationale

This is the only option that makes "no approval inferred from silence" a structurally enforced property rather than a documentation claim, satisfying both constitution Principle III and the governance guide's explicit failure trap "approval inferred from silence."

## Consequences

- **Positive**: approval evidence is structurally real, not just claimed; directly unit-testable (assert the graph has no auto-transition out of a human-gate node).
- **Negative**: requires the reviewer/candidate to take an explicit action to progress any run past a gate — by design, not a flaw.
- **Operational**: a run can remain parked indefinitely at a gate with no adverse effect (no timeout cleanup needed for the prototype).
- **Testing**: a dedicated test suite specifically asserts the absence of auto-advance transitions for every human-gate node.
- **Governance**: `decided_by` ties every approval to the human candidate's identity for this single-operator assessment context; documented as a prototype simplification (no multi-user RBAC) versus a production system.

## Risks and Mitigations

- Risk: a future task accidentally adds a system transition out of a gate node. Mitigation: the graph-definition test (above) fails CI if this happens — a structural regression test, not just a one-time check.

## Reversibility

High — approval mechanics are isolated to the orchestration API layer and `approval_records` schema; does not affect domain (shortener) code.

## Traceability

- Requirements: FR-013, FR-017
- Spec sections: Human-in-the-Loop Controls
- Plan sections: §5
- Expected tasks: approval-gates task group

## Validation

Validated by: a unit test asserting no auto-advance transition exists for any human-gate node, and an integration test exercising an actual approve/reject call against a parked run.
