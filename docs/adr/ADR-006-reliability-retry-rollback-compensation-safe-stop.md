# ADR-006: Retry, Fallback, Rollback/Compensation, and Safe-Stop Policy

## Status

Accepted — approved by human candidate (Belede Rahul), 2026-10-12

## Context

Constitution Principle VIII requires bounded retry, defined fallback, a distinction between rollback and compensation, and defined safe-stop conditions with controlled resumption.

## Decision Drivers

- Retries must be bounded and classified (transient vs. permanent) — unlimited retry is an explicit failure trap
- Rollback claims must be technically feasible, not asserted where infeasible
- Safe-stop must have a real trigger and a real, human-gated resume path

## Options Considered

### Option 1: Classification-driven bounded retry (max 2 retries, exponential backoff) + explicit rollback/compensation boundary by "has the change left the sandbox" + safe-stop on retry exhaustion or detected defect, human-only resume

- Advantages: each mechanism has a precise, testable trigger condition; rollback is only ever claimed where a change is still reversible (e.g., an uncommitted file); compensation is used once a change has propagated somewhere a clean undo cannot reach (e.g., an already-applied sandbox migration) — this mirrors how the real engineering fix for a path-resolution defect was handled in practice (regression test + fix, then human-approved resume)
- Disadvantages: requires explicit failure classification logic (transient vs. permanent) rather than a blanket retry-everything approach
- Risks: misclassifying a permanent failure as transient would cause wasted retries — mitigated by a narrow, explicit transient-failure allowlist (DB connection/I/O errors only)
- Implementation impact: medium
- Assessment implications: directly demonstrable via a forced-fault test and a real safe-stop→fix→resume sequence

### Option 2: Unlimited retry until success

- Advantages: simplest to write
- Disadvantages: explicit failure trap named in the governance guide ("unlimited retries"); can mask a permanent defect as a transient hiccup indefinitely
- Risks: fails constitutional requirement outright
- Implementation impact: n/a — rejected

### Option 3: No retry, no rollback, immediate safe-stop on any failure

- Advantages: maximally simple, maximally safe
- Disadvantages: does not demonstrate retry/fallback/rollback/compensation capability at all — fails the assignment's explicit requirement to demonstrate these mechanisms
- Risks: fails assignment core requirements
- Implementation impact: n/a — rejected

## Decision

Adopt **Option 1**. Retry: transient failures only (DB/I/O errors), max 2 retries, exponential backoff 1s→2s→4s, retry-exhausted → `SAFE_STOP`. Fallback: `DOCUMENT` node degrades to a labeled stub changelog on doc-generator failure rather than blocking the whole run. Rollback: used only for not-yet-externally-applied changes. Compensation: used once a change has propagated beyond clean rollback reach; always human-approved. Safe-stop: entered on retry exhaustion, a detected verification-node defect, or any attempted bypass of a human gate; resume is a separate, explicit, human-only action that re-enters the graph at the failed node only.

## Rationale

This gives every reliability mechanism a precise, testable trigger rather than a vague claim, and directly maps to the kind of real recovery evidence ("safe-stop → fix → human resume") the governance guide calls out as the strongest form of evidence — a bug is caught, fixed test-first, committed, and only then does a human-authorized resume continue the run.

## Consequences

- **Positive**: every reliability claim in the final documentation is backed by an executable test; the safe-stop/resume sequence produces genuinely strong audit evidence.
- **Negative**: more implementation surface than a naive approach (explicit classification logic, two distinct recovery code paths).
- **Operational**: a safe-stopped run is inert until a human calls the resume action; no automatic cleanup needed.
- **Testing**: dedicated tests for retry-bounds, fallback-trigger, rollback-path, compensation-path, and safe-stop→resume are all required deliverables (tasks.md).
- **Governance**: compensation actions are logged with the same rigor as approvals (actor, timestamp, reason, affected state) per Principle IX.

## Risks and Mitigations

- Risk: a genuinely transient failure is misclassified as permanent, causing an unnecessary safe-stop. Mitigation: the transient-failure allowlist is narrow and explicit, and is itself unit-tested against both allowlisted and non-allowlisted exception types.

## Reversibility

Moderate — retry/backoff constants are trivially tunable; the rollback-vs-compensation boundary logic is more structural and would need deliberate revision if the underlying persistence model changed (ADR-002).

## Traceability

- Requirements: FR-022, FR-023, FR-024, NFR-002
- Spec sections: Edge Cases; Non-Functional Requirements
- Plan sections: §6
- Expected tasks: retry-and-timeout, fallback, rollback-or-compensation, safe-stop task groups

## Validation

Validated by: forced-fault retry test, fallback-trigger test, rollback test, compensation test, and the real safe-stop→fix→resume sequence captured during the evidence runs (docs/scenarios/).
